import re

def resolve_expression(expr, parameter_table=None):
    expr = str(expr).strip()

    # Convert SystemVerilog-style literals (e.g. 16'h4000, 8'd255, 32'b101010)
    def sv_number_to_python(match):
        raw = match.group(0)
        try:
            if "'" in raw:
                _, radix_value = raw.split("'")
                radix = radix_value[0].lower()
                value = radix_value[1:].replace("_", "")  # Remove underscores
                if radix == 'h':
                    return str(int(value, 16))
                elif radix == 'd':
                    return str(int(value, 10))
                elif radix == 'b':
                    return str(int(value, 2))
                elif radix == 'o':
                    return str(int(value, 8))
        except Exception:
            raise ValueError(f"Could not parse SV literal: {raw}")
        return raw  # fallback

    # Replace SV literals before parameter substitution
    expr = re.sub(r"\d*'[hdbonHDBON][0-9a-fA-F_]+", sv_number_to_python, expr)

    def python_literal_to_int(match):
        raw = match.group(0)
        try:
            return str(int(raw, 0))  # Python auto-detects 0x / 0b / 0o / decimal
        except Exception:
            raise ValueError(f"Could not parse numeric literal: {raw}")

    # Regex: match 0x..., 0b..., 0o..., or plain decimal numbers
    expr = re.sub(r"\b(0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|\d+)\b", python_literal_to_int, expr)

    # Replace parameters using token-aware substitution
    if parameter_table:
        # Longer names first to prevent partial collisions
        for param in sorted(parameter_table.keys(), key=lambda p: -len(p)):
            val = str(parameter_table[param])
            expr = re.sub(rf"\b{re.escape(param)}\b", val, expr)

    if re.search(r"[a-zA-Z_]\w*", expr):
        return None  # Still contains unresolved variables

    # Evaluate arithmetic expression
    try:
        result = eval(expr, {"__builtins__": None}, {})
        return result
    except Exception:
        raise ValueError(f"Could not evaluate expression: {expr}")

def reorder_tree(data):
        """
        Reorder tuples into tree order (depth-first).
        Ensures:
        - Parent before child
        - Child before grandchild
        - Roots and siblings sorted by parse index (last element in tuple)
        - Works for arbitrary depth (n-levels deep)
        """
        result = {}

        for cpu, tuples in data.items():
            # Group children by parent
            children = {}
            for t in tuples:
                parent = t.module_parent  # parent reference
                children.setdefault(parent, []).append(t)

            # Sort children of each parent by parse order (second to last element in tuple)
            for parent in children:
                children[parent].sort(key=lambda x: x.id_count)

            ordered = []

            def dfs(parent):
                if parent in children:
                    for child in children[parent]:
                        ordered.append(child)
                        dfs(child.module_name)  # recurse into this child's children

            # Find roots (those whose parent is not listed as a child)
            all_children = {t.module_name for t in tuples}
            roots = [t for t in tuples if t.module_parent not in all_children]

            # Sort roots by parse order too
            roots.sort(key=lambda x: x.id_count)

            for root in roots:
                ordered.append(root)
                dfs(root.module_name)

            result[cpu] = ordered

        return result

def build_parameter_table(cpu_config):
    for _ in cpu_config.items():
        parameter_table = {}

        # Flatten all parameters
        all_parameters = {}
        for param_section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            all_parameters.update(cpu_config.get(param_section, {}))

        unresolved = {name: data.get("value") for name, data in all_parameters.items()}
        max_attempts = len(unresolved)

        for attempt in range(max_attempts):
            progress_made = False
            for name, val in list(unresolved.items()):
                try:
                    result = resolve_expression(val, parameter_table)
                    if result is not None:
                        resolved_value = int(result)
                        parameter_table[name] = resolved_value
                        unresolved.pop(name)
                        #print(f"[PASS {attempt+1}] Resolved {name} = {resolved_value}")
                        progress_made = True
                except Exception as e:
                    raise RuntimeError(f"Failed to resolve '{name}': {e}") from e

            if not progress_made:
                #print(f"[INFO] No progress made on pass {attempt+1}")
                break

        for name, val in unresolved.items():
            raise RuntimeError(f"Unresolved: {name} = {val}")
            
    return parameter_table

def assign_auto_addresses(parsed_configs, submodule_reg_map, alignment=4, reg_width_bytes=4):
    """
    Assigns memory addresses to modules with 'auto': True using BaseAddress and overlap avoidance.
    Handles symbolic expressions and scans forward from BaseAddress using proper masking.
    """

    def find_free_address(used_ranges, needed_size, start_from=0x0000):
        used_sorted = sorted(used_ranges, key=lambda r: r[0])
        addr = (start_from + alignment - 1) & ~(alignment - 1)

        for start, end in used_sorted:
            end_addr = addr + needed_size - 1
            if end_addr < start:
                return addr
            if addr <= end:
                addr = (end + 1 + alignment - 1) & ~(alignment - 1)
        return addr

    for _, cpu_config in parsed_configs.items():

        global_mask = []  # Tracks all used address ranges globally

        # Step 2: Process sections independently
        for section_name in ["BUILTIN_MODULES", "USER_MODULES"]:
            section = cpu_config.get(section_name, {})
            if not isinstance(section, dict):
                continue

            # Step 3: Resolve section BaseAddress
            base_expr = section.get("BaseAddress")
            try:
                section_ptr = (base_expr if base_expr else 0x0000)
                section_ptr = (section_ptr + alignment - 1) & ~(alignment - 1)
            except Exception:
                raise RuntimeError(f"Could not resolve BaseAddress for {section_name}")

            # Step 4: Build local address mask for this section
            def overlaps(new_range, existing_ranges):
                s, e = new_range
                return any(not (e < xs or s > xe) for xs, xe in existing_ranges)
            local_mask = []
            for mod_name, mod in section.items():
                if mod_name == "BaseAddress" or not isinstance(mod, dict):
                    continue
                if "submodule_of" in mod:
                    continue

                bounds = mod.get("bounds")
                enabled = mod.get("flag")
                if bounds and isinstance(bounds, list) and len(bounds) == 2:
                    try:
                        start = bounds[0]
                        end = bounds[1]
                        if start % alignment != 0 or end % alignment != 0:
                            raise ValueError(f"Invalid Address Range for {mod_name}: [{start}:{end}]. Expects {alignment} byte alignment.")
                        if start is not None and end is not None:
                            if enabled == "TRUE":
                                if overlaps((start, end), global_mask):
                                    print(f"Warning: {mod_name} bounds {start:#04X}-{end:#04X} overlap with existing ranges")
                                local_mask.append((start, end))
                                global_mask.append((start, end)) 
                        else:
                            raise RuntimeWarning(f"Skipping unresolved bounds for {mod_name}: {bounds}")
                    except Exception:
                        raise RuntimeError(f"Could not resolve bounds for {mod_name}: {bounds}")

            # Step 5: Assign auto modules
            for mod_name, mod in section.items():
                if mod_name == "BaseAddress" or not isinstance(mod, dict):
                    continue

                if "submodule_of" in mod:
                    continue

                if mod.get("flag") == "TRUE" and mod.get("auto", False):
                    raw_reg_count = mod.pop("registers", 0)
                    try:
                        reg_count = raw_reg_count
                    except Exception:
                        raise RuntimeError(f"Failed to resolve register count for {mod_name}")

                    mod.pop("auto", None)
                    if reg_count < 1:
                        raise ValueError(f"Invalid register count for {mod_name}")

                    needed_size = reg_count * reg_width_bytes
                    start_addr = find_free_address(global_mask + local_mask, needed_size, section_ptr)
                    end_addr = start_addr + (reg_count - 1) * reg_width_bytes

                    mod["bounds"] = [start_addr, end_addr]

                    #print(f"\n[DEBUG] Attempting to assign '{mod_name}'")
                    #print(f"[DEBUG] Raw registers: {raw_reg_count}")
                    #print(f"[DEBUG] Resolved register count: {reg_count}")
                    #print(f"[DEBUG] Needed size: {needed_size}")
                    #print(f"[DEBUG] Starting from section BaseAddress: 0x{section_ptr:X}")
                    #print(f"[DEBUG] Global mask: {[f'{s:#06X}-{e:#06X}' for s, e in global_mask]}")
                    #print(f"[DEBUG] Local mask: {[f'{s:#06X}-{e:#06X}' for s, e in local_mask]}")

                    # Track new range
                    local_mask.append((start_addr, end_addr))
                    global_mask.append((start_addr, end_addr))
                    #section_ptr = end_addr + 1
                    #print(f"[DEBUG] Assigned bounds for '{mod_name}': {mod['bounds']}")

            # Step 6: Clean up BaseAddress
            section.pop("BaseAddress", None)

    submodule_reg_map = reorder_tree(submodule_reg_map)

    submodule_mask = []
    current_base_module_start_addr = 0
    current_base_module_end_addr = 0
    current_base_module = ""
    current_base_module_subregister_count = 0
    for cpu, data in submodule_reg_map.items():
        for submodule in data:
            if current_base_module != submodule.base_module:
                current_base_module = submodule.base_module
                submodule_mask = []
                current_base_module_start_addr = parsed_configs[cpu][submodule.section][submodule.base_module]["bounds"][0]
                current_base_module_end_addr = parsed_configs[cpu][submodule.section][submodule.base_module]["bounds"][1]
                current_base_module_subregister_count = parsed_configs[cpu][submodule.section][submodule.base_module]["subregisters"]
                current_base_module_start_addr += 4*(int((current_base_module_end_addr-current_base_module_start_addr)//alignment + 1) - (current_base_module_subregister_count))

            start_addr = find_free_address(submodule_mask, max(1, submodule.register_count)*alignment, current_base_module_start_addr)
            end_addr = start_addr + (submodule.register_count-1)*alignment
            submodule_mask.append((start_addr, end_addr))
            if "subregisters" in parsed_configs[cpu][submodule.section][submodule.module_name]:
                end_addr += parsed_configs[cpu][submodule.section][submodule.module_name]["subregisters"]*alignment
            parsed_configs[cpu][submodule.section][submodule.module_name]["bounds"] = [start_addr, end_addr]
