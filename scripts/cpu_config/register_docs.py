def dump_all_registers_from_configs(parsed_configs, submodule_reg_map, file_path, file_name="cpu_registers.txt", print_to_console=True, save_to_file=False, reg_width_bytes=4, user_modules_only=False):
    """
    Resolves symbolic expressions and dumps register addresses with metadata for all CPUs.
    ASCII-only output with clean indentation and structured formatting.
    """
    lines = []
    lines.append("Register Address Map")
    lines.append("====================")

    for cpu_name, cpu_config in parsed_configs.items():
        lines.append("")
        lines.append(f"Instance: {cpu_name}")

        section_list = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in section_list:
            if cpu_config.get(section, {}).items(): # Dont print USER_MODULES section if none are present
                lines.append("")
                lines.append(f"    Section: {section}")

            for module_name, module in cpu_config.get(section, {}).items():
                module_name_orig = module_name
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE":
                    continue
                if "bounds" not in module:
                    lines.append(f"    Warning: {module_name} missing bounds")
                    continue

                try:
                    start_addr = module["bounds"][0]
                    end_addr = module["bounds"][1]
                    if "subregisters" in module:
                        subregisters = module["subregisters"]
                    else:
                        subregisters = 0
                except Exception as e:
                    lines.append(f"    Error in {module_name}: {e}")
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                if "submodule_of" in module:
                    for submodule in submodule_reg_map.get(cpu_name):
                        if submodule.module_name == module_name:
                            submodule_indent = "    " * submodule.module_name.count(submodule.separator)
                            module_name = str(module_name.split(submodule.separator)[-1])
                            base_module_reg_expand = submodule.base_reg_exp
                            break
                else:
                    submodule_indent = ""
                    base_module_reg_expand = ""

                if base_module_reg_expand == "TRUE":
                    continue
                    
                # Module metadata
                mod_meta = module.get("metadata", {})
                mod_name_str = mod_meta.get("name", module_name)
                mod_desc_str = mod_meta.get("description", "")
                mod_reg_expand_str = mod_meta.get("expand_regs", '')
                mod_repeat_inst = mod_meta.get("repeat_instance", {})
                mod_repeat_info = module.get("repeat", {"value": {}, "expand_regs": {}, "repeat_of": {}})
                mod_repeat_str = f" - Repeat Instance of {mod_repeat_info['repeat_of']}" if mod_repeat_inst else ""

                lines.append("")
                if submodule_indent:
                    lines.append(f"{submodule_indent}        -> Submodule: {mod_name_str} ({module_name}){mod_repeat_str}")
                else:
                    lines.append(f"{submodule_indent}        -> Module: {mod_name_str} ({module_name}){mod_repeat_str}")
                lines.append(f"{submodule_indent}            - Bounds: 0x{start_addr:04X} ({start_addr:0d}) to 0x{end_addr:04X} ({end_addr:0d})")
                if mod_repeat_inst != 'TRUE' or (mod_repeat_info["expand_regs"] == 'FALSE' and mod_reg_expand_str == 'FALSE'):
                    lines.append(f"{submodule_indent}            - Register Count: {reg_count}")
                if (mod_desc_str and not mod_repeat_inst) or (mod_repeat_info["expand_regs"] == 'FALSE' and mod_reg_expand_str == 'FALSE' and mod_repeat_inst):
                    indent = " " * 12
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"{submodule_indent}{indent}- Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n{submodule_indent}{indent}               {line}"
                    lines.append(formatted_desc)

                # Register metadata
                if ((mod_reg_expand_str == 'FALSE' and not mod_repeat_inst) or (mod_repeat_info["expand_regs"] == 'FALSE' and mod_reg_expand_str == 'FALSE')):
                    for i in range(reg_count-subregisters):
                        reg_addr = start_addr + i * reg_width_bytes
                        reg_key = f"Reg{i}"
                        reg_info = module.get("regs", {}).get(reg_key, {})
                        reg_name_str = reg_info.get("name", f"Reg{i}")
                        reg_desc_str = reg_info.get("description", "")
                        reg_perm_str = reg_info.get("permissions", "")

                        lines.append("")
                        lines.append(f"{submodule_indent}            -> {reg_key}: {reg_name_str}")
                        lines.append(f"{submodule_indent}                - Address: 0x{reg_addr:04X} ({reg_addr:0d})")
                        if reg_desc_str:
                            indent = " " * 16
                            desc_lines = reg_desc_str.split('\n')
                            formatted_desc = f"{submodule_indent}{indent}- Description: {desc_lines[0]}"
                            for line in desc_lines[1:]:
                                formatted_desc += f"\n{submodule_indent}{indent}               {line}"
                            lines.append(formatted_desc)
                        if reg_perm_str:
                            lines.append(f"{submodule_indent}                - Permissions: {reg_perm_str}")

                        fields = reg_info.get("fields", {})
                        for field_key, field_info in fields.items():
                            fname = field_info.get("name", field_key)
                            fbounds = field_info.get("bounds", [])
                            try:
                                fupper = fbounds[0]
                                flower = fbounds[1]
                                if fupper == None or flower == None or fupper < 0 or flower < 0:
                                    raise SyntaxError(f"Field Bounds for {module_name_orig} is not valid")
                            except:
                                raise SyntaxError(f"Field Bounds for {module_name_orig} is not valid")
                            fdesc = field_info.get("description", "")
                            lines.append(f"{submodule_indent}                -> {field_key}: {fname}")
                            lines.append(f"{submodule_indent}                    - Bits: [{fupper}:{flower}]")
                            if fdesc:
                                desc_lines = fdesc.split('\n')
                                formatted_desc = f"{submodule_indent}                    - Description: {desc_lines[0]}"
                                for line in desc_lines[1:]:
                                    formatted_desc += f"\n{submodule_indent}                                   {line}"
                                lines.append(formatted_desc)

    output = "\n".join(lines)
    if (print_to_console == True):
        print(output)

    if save_to_file:
        combined_file_path = file_path+"/"+file_name
        with open(combined_file_path, "w") as f:
            f.write(output)
        print(f"\nRegister map saved to: {combined_file_path}")

def dump_all_registers_html(parsed_configs, submodule_reg_map, file_path,
                            file_name="cpu_registers.html",
                            print_to_console=True, save_to_file=False,
                            reg_width_bytes=4, user_modules_only=False,
                            dark_mode=True):
    """
    HTML version of dump_all_registers_from_configs.
    Supports N-level deep submodules using separator-based depth,
    and lists all modules in the sidebar.
    """

    # -----------------------------
    # CSS / HTML header
    # -----------------------------
    if dark_mode:
        bg_color = "#121212"
        text_color = "#e0e0e0"
        nav_bg = "#1e1e1e"
        nav_border = "#333"
        link_color = "#e0e0e0"
        link_hover = "#80cbc4"
    else:
        bg_color = "#ffffff"
        text_color = "#000000"
        nav_bg = "#f7f7f7"
        nav_border = "#ccc"
        link_color = "#333"
        link_hover = "#007acc"

    header = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='UTF-8'>",
        "<title>Register Map</title>",
        "<style>",
        f"body {{ display: flex; font-family: monospace; margin:0; background-color: {bg_color}; color: {text_color}; }}",
        f"nav {{ width: 260px; background: {nav_bg}; padding: 12px; border-right: 1px solid {nav_border};",
        "      height: 100vh; overflow-y: auto; overflow-x: hidden; position: fixed; color: inherit; }}",
        "nav h3 { margin: 8px 0; }",
        "nav ul { list-style-type: none; padding-left: 0; margin: 0; }",
        "nav li { margin: 4px 0; }",
        f"nav a {{ text-decoration: none; color: {link_color}; text-decoration: none; }}",
        f"nav a:hover {{ color: {link_hover}; }}",
        "main { margin-left: 280px; padding: 20px; flex: 1; }",
        f"h2, h3, h4 {{ margin-top: 20px; color: {text_color}; }}",
        "ul { margin-left: 20px; }",
        "</style></head><body>"
    ]

    sidebar = ["<nav><h3>CPUs</h3>"]
    content = ["<main><h1>Register Address Map</h1>"]

    # -----------------------------
    # Main CPU loop
    # -----------------------------
    for cpu_name, cpu_config in parsed_configs.items():
        sidebar.append(f"<details open><summary>CPU Instance: {cpu_name}</summary><ul>")
        content.append(f"<details open><summary>Instance: {cpu_name}</summary>")

        section_list = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in section_list:
            section_modules = cpu_config.get(section, {})
            if not section_modules:
                continue

            content.append(f"<h3>Section: {section}</h3>")

            # Preprocess modules: compute display name, depth, base_reg_expand
            processed_modules = []
            for module_name, module in section_modules.items():
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE":
                    continue
                if "bounds" not in module:
                    # Skip in HTML; you can add a warning if you want
                    continue

                module_name_orig = module_name
                depth = 0
                display_name = module_name
                base_module_reg_expand = ""

                if "submodule_of" in module:
                    # Match submodule info from submodule_reg_map (attribute style)
                    for sub in submodule_reg_map.get(cpu_name, []):
                        if getattr(sub, "module_name", None) == module_name_orig:
                            sep = getattr(sub, "separator", ".")
                            depth = module_name_orig.count(sep)
                            display_name = module_name_orig.split(sep)[-1]
                            base_module_reg_expand = getattr(sub, "base_reg_exp", "")
                            break
                # Non-submodule
                module["_orig_name"] = module_name_orig
                module["_display_name"] = display_name
                module["_depth"] = depth
                module["_base_reg_expand"] = base_module_reg_expand

                processed_modules.append((module_name_orig, module))

            # Sidebar: flat list, indented by depth
            for module_name_orig, module in processed_modules:
                if module["_base_reg_expand"] == "TRUE":
                    continue

                depth = module["_depth"]
                disp = module["_display_name"]
                label = module.get("metadata", {}).get("name", disp)
                indent_px = 12 * depth
                mod_id = f"{cpu_name}_{section}_{module_name_orig}"

                sidebar.append(
                    f"<li style='margin-left:{indent_px}px;'><a href='#{mod_id}'>{label}</a></li>"
                )

            # Content: modules + registers
            for module_name_orig, module in processed_modules:
                if module["_base_reg_expand"] == "TRUE":
                    continue

                try:
                    start_addr = module["bounds"][0]
                    end_addr = module["bounds"][1]
                    subregisters = module.get("subregisters", 0)
                except Exception as e:
                    content.append(f"<p>Error in {module_name_orig}: {e}</p>")
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1

                depth = module["_depth"]
                disp = module["_display_name"]
                mod_meta = module.get("metadata", {})
                mod_name_str = mod_meta.get("name", disp)
                mod_desc_str = mod_meta.get("description", "")
                mod_reg_expand_str = mod_meta.get("expand_regs", '')
                mod_repeat_inst = mod_meta.get("repeat_instance", {})
                mod_repeat_info = module.get("repeat", {"value": {}, "expand_regs": {}, "repeat_of": {}})
                mod_repeat_str = f" - Repeat Instance of {mod_repeat_info['repeat_of']}" if mod_repeat_inst else ""

                indent_px = 40 * depth
                style = f" style='margin-left:{indent_px}px;'"
                mod_id = f"{cpu_name}_{section}_{module_name_orig}"

                label = "Submodule" if depth > 0 else "Module"
                content.append(f"<h3 id='{mod_id}'{style}>{label}: {mod_name_str} ({disp}){mod_repeat_str}</h3>")
                content.append(
                    f"<p{style}>Bounds: 0x{start_addr:04X} ({start_addr:d}) to "
                    f"0x{end_addr:04X} ({end_addr:d})</p>"
                )

                if mod_repeat_inst != 'TRUE' or (mod_repeat_info.get("expand_regs") == 'FALSE' and mod_reg_expand_str == 'FALSE'):
                    content.append(f"<p{style}>Register Count: {reg_count}</p>")

                if (mod_desc_str and not mod_repeat_inst) or \
                   (mod_repeat_info.get("expand_regs") == 'FALSE' and mod_reg_expand_str == 'FALSE' and mod_repeat_inst):
                    desc_html = "<br>".join(mod_desc_str.split("\n"))
                    content.append(f"<p{style}>Description: {desc_html}</p>")

                # Registers
                # Only emit a table if THIS module actually has registers
                if ((mod_reg_expand_str == 'FALSE' and not mod_repeat_inst) or
                    (mod_repeat_info.get("expand_regs") == 'FALSE' and mod_reg_expand_str == 'FALSE')) \
                    and (reg_count - subregisters) > 0:

                    content.append(
                        f"<table style='margin-left:{indent_px}px; border-collapse:collapse; width:95%; "
                        f"margin-top:10px; margin-bottom:20px;'>"
                        "<tr style='border-bottom:1px solid #666;'>"
                        "<th style='text-align:left; padding:4px;'>Register</th>"
                        "<th style='text-align:left; padding:4px;'>Address</th>"
                        "<th style='text-align:left; padding:4px;'>Permissions</th>"
                        "<th style='text-align:left; padding:4px;'>Description</th>"
                        "<th style='text-align:left; padding:4px;'>Fields</th>"
                        "</tr>"
                    )

                    for i in range(reg_count - subregisters):
                        reg_addr = start_addr + i * reg_width_bytes
                        reg_key = f"Reg{i}"
                        reg_info = module.get("regs", {}).get(reg_key, {})
                        reg_name_str = reg_info.get("name", reg_key)
                        reg_desc_str = reg_info.get("description", "")
                        reg_perm_str = reg_info.get("permissions", "")

                        # Build field table if present
                        fields = reg_info.get("fields", {})
                        if fields:
                            field_table = [
                                "<table style='border-collapse:collapse; width:100%;'>",
                                "<tr><th style='text-align:left;'>Field</th>"
                                "<th style='text-align:left;'>Bits</th>"
                                "<th style='text-align:left;'>Description</th></tr>"
                            ]
                            for field_key, field_info in fields.items():
                                fname = field_info.get("name", field_key)
                                fbounds = field_info.get("bounds", [])
                                fupper, flower = fbounds
                                fdesc = field_info.get("description", "")
                                field_table.append(
                                    f"<tr>"
                                    f"<td>{fname}</td>"
                                    f"<td>[{fupper}:{flower}]</td>"
                                    f"<td>{fdesc}</td>"
                                    f"</tr>"
                                )
                            field_table.append("</table>")
                            field_html = "".join(field_table)
                        else:
                            field_html = ""

                        # Add register row
                        content.append(
                            "<tr style='border-bottom:1px solid #333;'>"
                            f"<td style='padding:4px;'>{reg_name_str}</td>"
                            f"<td style='padding:4px;'>0x{reg_addr:04X}</td>"
                            f"<td style='padding:4px;'>{reg_perm_str}</td>"
                            f"<td style='padding:4px;'>{reg_desc_str.replace(chr(10), '<br>')}</td>"
                            f"<td style='padding:4px;'>{field_html}</td>"
                            "</tr>"
                        )

                    content.append("</table>")


                    content.append(f"<hr style='border:0; border-top:8px solid #444; margin:{20 + depth*10}px 0;'>")


        content.append("</details>")
        sidebar.append("</ul></details>")

    content.append("</main>")
    sidebar.append("</nav>")
    footer = ["</body></html>"]

    output = "\n".join(header + sidebar + content + footer)

    if print_to_console:
        print(output)

    if save_to_file:
        combined_file_path = file_path + "/" + file_name
        with open(combined_file_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nRegister map saved to: {combined_file_path}")
