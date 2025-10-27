import csv
import re
import sys
from typing import List, Tuple, Dict, Set, Iterable

# --- ANSI Color Codes ---
COLORS: List[str] = [
    "\033[41m",   # Red
    "\033[42m",   # Green
    "\033[44m",   # Blue
    "\033[45m",   # Magenta
    "\033[46m",   # Cyan
    
    # High-contrast 256-Color Palette (Kept as they offer good differentiation)
    "\033[48;5;208m", # Orange
    "\033[48;5;52m",  # Dark Red (Maroon)
    "\033[48;5;22m",  # Dark Green
    "\033[48;5;129m", # Purple
    "\033[48;5;177m", # Pink
    "\033[48;5;19m",  # Dark Blue
    "\033[48;5;28m",  # Forest Green
    "\033[48;5;135m", # Lavender
    "\033[48;5;202m", # Deep Orange
    "\033[48;5;36m",  # Dark Cyan
]
RESET: str = "\033[0m"
TEXT_BOLD_ITALIC_STATE: str = "\033[1m\033[3m" 
PIN_TERMINATOR: str = "\033[22m\033[23m\033[49m"
NEUTRAL_BACKGROUND: str = "\033[40m"

# --- ISOLATED P-GROUP COLORS ---
ISOLATED_LABEL_COLOR: str = "\033[34m\033[1m" # Blue text, Bold for the 'Shorted' label
ISOLATED_PIN_COLOR: str = "\033[44m"           # Blue background for the P pins
# ---

# Global list for dynamically loaded prefixes (e.g., ['A', 'B'])
GRID_PREFIXES: List[str] = []
# Global dictionary to store prefix-specific dimensions: {'A': (3, 4), 'B': (5, 4), ...}
GRID_DIMENSIONS: Dict[str, Tuple[int, int]] = {}
# The width of a single cell in the ASCII chart (used for padding)
GLOBAL_CELL_WIDTH: int = 8 
# The constant separator for all grid columns
GRID_SEPARATOR: str = "  "

# NEW GLOBAL: E2E Pins (e.g., ['GND', 'TIP'] read from config)
E2E_PINS: List[str] = []

# --- Consolidated File Reading Helper ---

def get_non_comment_lines(file_path: str) -> List[str]:
    """Reads a file and returns a list of lines, excluding comments (#) and empty lines."""
    lines: List[str] = []
    try:
        with open(file_path, mode='r') as file:
            for line in file:
                line_stripped = line.strip()
                # Ignore comment lines and entirely empty lines
                if line_stripped.startswith('#') or not line_stripped:
                    continue
                lines.append(line)
    except FileNotFoundError:
        pass 
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return lines

# --- Core Helper Functions ---

def is_grid_definition(item: str) -> bool:
    """Checks if an item is formatted like a grid definition (X:CxR), case-insensitive."""
    return bool(re.match(r'^[A-Z]:\d+x\d+$', item.strip(), re.IGNORECASE))

def is_e2e_pin_definition(item: str) -> bool:
    """Checks if an item is formatted like an e2epins definition."""
    return item.strip().lower().startswith('e2epins:')

def is_pin(item: str) -> bool:
    """Checks if an item is a switch pin (X<num>) where X is a recognized prefix."""
    if not GRID_PREFIXES:
        return bool(re.match(r'^[A-Z]\d+$', item)) 
        
    match = re.match(r'^([A-Z])(\d+)$', item)
    if match and match.group(1) in GRID_PREFIXES:
        return True
    return False

def is_p_element(item: str) -> bool:
    """
    Checks if an item is a P-element (P<num><sign>).
    Also ensures it is *not* one of the E2E pins, as they are separate categories.
    """
    return bool(re.match(r'^P\d[+-]$', item)) and (item not in E2E_PINS)

def is_external_element(item: str) -> bool:
    """Checks if an item is an external element (P-element or E2E pin)."""
    return is_p_element(item) or (item in E2E_PINS)

def load_all_configs(file_path: str) -> Tuple[int, int, List[str]]:
    """
    Reads data.csv to find all grid prefixes and their specific dimensions, 
    and to load E2E pins.
    """
    prefixes: Set[str] = set()
    max_C: int = 3
    max_R: int = 4
    
    global GRID_DIMENSIONS, E2E_PINS
    GRID_DIMENSIONS = {}
    E2E_PINS = []
    
    lines = get_non_comment_lines(file_path)
    
    if lines:
        for line in lines:
            line_stripped = line.strip()
            
            # --- Grid Definitions ---
            matches = re.findall(r'([A-Z]):(\d+)x(\d+)', line_stripped, re.IGNORECASE)
            for prefix, c_str, r_str in matches:
                prefix_upper = prefix.upper()
                C_val = int(c_str)
                R_val = int(r_str)
                
                if prefix_upper not in GRID_DIMENSIONS:
                    GRID_DIMENSIONS[prefix_upper] = (C_val, R_val)
                    prefixes.add(prefix_upper)
                    max_C = max(max_C, C_val)
                    max_R = max(max_R, R_val)
                    
            # --- E2E Pin Definitions ---
            if is_e2e_pin_definition(line_stripped):
                # Extract the list after 'e2epins:'
                pin_list_str = line_stripped[len('e2epins:'):].strip()
                # Use csv reader logic to handle various delimiters/formats
                try:
                    reader = csv.reader([pin_list_str])
                    E2E_PINS.extend([item.strip().upper() for item in next(reader) if item.strip()])
                    E2E_PINS = list(dict.fromkeys(E2E_PINS)) # Remove duplicates while preserving order
                except Exception:
                    # Fallback for simple comma/space separated list if CSV parsing fails
                    E2E_PINS = [p.strip().upper() for p in re.split(r'[,\s]+', pin_list_str) if p.strip()]


        
    global GRID_PREFIXES 
    GRID_PREFIXES = sorted(list(prefixes))
    
    # If E2E pins weren't defined, default to 'G' and 'T' for backward compatibility
    if not E2E_PINS:
        E2E_PINS = ['G', 'T']
        
    return max_C, max_R, GRID_PREFIXES

def load_data(file_path: str) -> List[List[str]]:
    """Loads and returns all connection data lines from a CSV file, ignoring config lines."""
    all_data_lines: List[List[str]] = []
    
    # FIXED: Corrected function call
    raw_lines = get_non_comment_lines(file_path)

    filtered_lines = []
    for line in raw_lines:
        if is_grid_definition(line) or is_e2e_pin_definition(line): 
             continue
        filtered_lines.append(line)
        
    if filtered_lines:
        reader = csv.reader(filtered_lines)
        all_data_lines = [
            [item.strip() for item in line if item and not is_grid_definition(item.strip()) and not is_e2e_pin_definition(item.strip())] 
            for line in reader 
            if [item for item in line if item and not is_grid_definition(item.strip()) and not is_e2e_pin_definition(item.strip())]
        ]
            
    return all_data_lines

def load_state_data_as_groups(file_path: str, prefix: str) -> List[List[str]]:
    """Loads state data and converts each line into a prefixed group list."""
    state_groups = []
    
    raw_lines = get_non_comment_lines(file_path)

    if raw_lines:
        reader = csv.reader(raw_lines)
        for line_data in reader:
            group = set()
            for raw_item in filter(None, line_data):
                if is_grid_definition(raw_item) or is_e2e_pin_definition(raw_item):
                    continue

                parts = re.split(r'[^A-Za-z0-9\+\-]+', raw_item) 
                
                for part in filter(None, parts):
                    part_upper = part.upper()
                    
                    if part.isdigit():
                        group.add(prefix + part)
                    elif re.match(r'^([A-Z])(\d+)$', part) and part.startswith(prefix):
                         group.add(part)
                    # Include P-elements AND E2E pins (now dynamically loaded)
                    elif is_p_element(part_upper) or (part_upper in E2E_PINS): 
                         group.add(part_upper)
                         
            if group:
                pins = sorted([item for item in group if is_pin(item)], key=lambda x: int(x[1:]))
                
                external = sorted([item for item in group if not is_pin(item) and not is_grid_definition(item) and not is_e2e_pin_definition(item)], key=str.upper)
                
                state_groups.append(external + pins)
                
    return state_groups

def load_state_pin_set(file_path: str, prefix: str) -> set:
    """Loads state data into a flat set of pin names."""
    state_pins = set()
    
    raw_lines = get_non_comment_lines(file_path)

    if not raw_lines:
        return state_pins
        
    reader = csv.reader(raw_lines)
    for line_data in reader:
        for raw_item in filter(None, line_data):
            
            if is_grid_definition(raw_item) or is_e2e_pin_definition(raw_item):
                continue
                
            parts = re.split(r'[^A-Za-z0-9\+\-]+', raw_item) 
            for part in filter(None, parts):
                
                if part.isdigit():
                    state_pins.add(prefix + part)
                elif re.match(r'^([A-Z])(\d+)$', part) and part.startswith(prefix):
                     state_pins.add(part)

    return state_pins

def reduce_connection_groups(initial_groups: List[List[str]]) -> List[List[str]]:
    """Merges overlapping groups and sorts the final list based on connection type priority."""
    if not initial_groups:
        return []

    working_groups: List[Set[str]] = [set(g) for g in initial_groups if g]
    merged_groups: List[Set[str]] = []

    while working_groups:
        current_group = working_groups.pop(0)
        i = 0
        while i < len(working_groups):
            if current_group.intersection(working_groups[i]):
                current_group.update(working_groups.pop(i))
                i = 0 
                continue
            i += 1
        merged_groups.append(current_group)


    final_reduced_groups: List[List[str]] = []
    for group_set in merged_groups:
        pins = sorted([item for item in group_set if is_pin(item)], key=lambda x: (x[0], int(x[1:])))
        
        # Sort external items alphabetically (case-insensitive)
        external = sorted([item for item in group_set if not is_pin(item) and not is_grid_definition(item) and not is_e2e_pin_definition(item)], key=str.upper)
        
        final_reduced_groups.append(external + pins) 

    def sort_key(group):
        if not group: return (3, 'z')
        external_count = sum(1 for item in group if not is_pin(item))
        
        # Check if any E2E pin is present
        has_e2e = any(item in E2E_PINS for item in group)
        
        if has_e2e:
            return (0, group[0])
        elif external_count > 0:
            return (1, group[0])
        else:
            return (2, group[0])

    final_reduced_groups.sort(key=sort_key)
    return final_reduced_groups

def generate_ascii_grid(prefix: str, C: int, R: int, cell_width: int) -> Tuple[List[str], Dict[str, Tuple[int, int]]]:
    """Generates the lines and a map of cell names to insertion points for a specific C x R grid."""
    
    grid_lines: List[str] = []
    coord_map: Dict[str, Tuple[int, int]] = {}
    dot_number: int = 1
    
    border_line: str = "+" + ("-" * cell_width + "+") * C
    grid_lines.append(border_line)
    for i in range(R):
        row_str: str = "|"
        for _ in range(C):
            cell_name: str = prefix + str(dot_number)
            line_index: int = 2 * i + 1
            closing_pipe_index: int = len(row_str) + cell_width
            coord_map[cell_name] = (line_index, closing_pipe_index)
            row_str += cell_name.center(cell_width) + "|"
            dot_number += 1
        
        grid_lines.append(row_str)
        if i < R - 1:
            grid_lines.append(border_line)
            
    grid_lines.append(border_line)
    
    return grid_lines, coord_map

def apply_coloring(lines: List[str], ops: List[Tuple[int, int, str]]) -> None:
    """Applies color/reset codes to grid lines, handling index shifts."""
    ops_by_line: Dict[int, List[Tuple[int, str]]] = {}
    for r, c_index, code in ops:
        if r not in ops_by_line: ops_by_line[r] = []
        ops_by_line[r].append((c_index, code))

    for r in sorted(ops_by_line.keys()):
        line_list: List[str] = list(lines[r])
        # Sort by index descending to avoid shifting issues
        for c_index, code in sorted(ops_by_line[r], key=lambda x: x[0], reverse=True):
            line_list.insert(c_index, code)
        lines[r] = "".join(line_list)


def calculate_global_colors(globally_reduced_groups: List[List[str]], map_coords: Dict[str, Dict[str, Tuple[int, int]]], state_pins_by_prefix: Dict[str, Set[str]], cell_width: int) -> Tuple[Dict[str, str], Dict[str, str], List[Tuple[int, int, str, str]], Set[str]]:
    """
    Calculates the definitive color maps for Part 3/4 with E2E priority.
    """
    pin_color_map: Dict[str, str] = {}
    external_color_map: Dict[str, str] = {}
    all_unique_external_items: Set[str] = set()
    consolidated_pin_ops: List[Tuple[int, int, str, str]] = []
    
    group_to_color: Dict[Tuple[str, ...], str] = {}
    for i, group in enumerate(globally_reduced_groups):
        group_to_color[tuple(group)] = COLORS[i % len(COLORS)]

    def group_priority_key(group):
        external_count = sum(1 for item in group if not is_pin(item))
        has_e2e = any(item in E2E_PINS for item in group)
        
        if has_e2e: return 0
        elif external_count > 0: return 1
        else: return 2
        
    sorted_groups = sorted(globally_reduced_groups, key=group_priority_key)

    for group in sorted_groups:
        color = group_to_color[tuple(group)]
        for item in group:
            if is_pin(item):
                if item not in pin_color_map:
                    pin_color_map[item] = color
            else:
                if not is_grid_definition(item) and not is_e2e_pin_definition(item):
                    external_color_map[item] = color
                    all_unique_external_items.add(item) 

    for item, color in pin_color_map.items():
        prefix = item[0]
        if prefix in map_coords:
            current_map: Dict[str, Tuple[int, int]] = map_coords[prefix]
            state_pins: Set[str] = state_pins_by_prefix.get(prefix, set())

            if item in current_map:
                r, c_end = current_map[item]
                c_start = c_end - cell_width
                text_format_code: str = TEXT_BOLD_ITALIC_STATE if item in state_pins else ""
                consolidated_pin_ops.append((r, c_end, PIN_TERMINATOR, prefix))
                consolidated_pin_ops.append((r, c_start, color + text_format_code, prefix))
            
    return pin_color_map, external_color_map, consolidated_pin_ops, all_unique_external_items

# --- Output Helpers ---

def render_external_connections_table(
    items: List[str],
    color_map: Dict[str, str],
    cell_width: int,
    label: str = "EXTERNAL"
) -> None:
    """
    Render a single-row table describing the external connections using the provided colors.
    """
    if not items:
        return

    print("\nALL EXTERNAL CONNECTIONS (Colored):")

    num_items = len(items)
    border_line: str = ("+" + "-" * cell_width) * num_items + "+"
    print(NEUTRAL_BACKGROUND + border_line + RESET)

    total_width = num_items * (cell_width + 1) - 1
    header_row = NEUTRAL_BACKGROUND + "|" + label.center(total_width) + "|" + RESET
    print(header_row)
    print(NEUTRAL_BACKGROUND + border_line + RESET)

    item_row = NEUTRAL_BACKGROUND + "|" + RESET
    for item in items:
        color: str = color_map.get(item, NEUTRAL_BACKGROUND)
        item_row += color + item.center(cell_width) + NEUTRAL_BACKGROUND + "|" + RESET
    print(item_row)
    print(NEUTRAL_BACKGROUND + border_line + RESET)

def build_colored_grid_lines(
    base_grid_lines: Dict[str, List[str]],
    consolidated_ops: List[Tuple[int, int, str, str]]
) -> Dict[str, List[str]]:
    """
    Clone the base grid lines and apply the provided coloring operations.
    """
    colored_lines: Dict[str, List[str]] = {p: list(base_grid_lines[p]) for p in GRID_PREFIXES}
    ops_by_prefix: Dict[str, List[Tuple[int, int, str]]] = {p: [] for p in GRID_PREFIXES}

    for r, c_index, code, prefix in consolidated_ops:
        ops_by_prefix[prefix].append((r, c_index, code))

    for prefix in GRID_PREFIXES:
        apply_coloring(colored_lines[prefix], ops_by_prefix[prefix])

    return colored_lines

def render_switch_grids(
    final_lines: Dict[str, List[str]],
    grid_height: int,
    note_text: str
) -> None:
    """
    Render the consolidated switch grid section with a shared header and note.
    """
    header_str = GRID_SEPARATOR.join([f"SWITCH {p}" for p in GRID_PREFIXES])

    print(f"\n{header_str}")
    print(note_text)
    for i in range(grid_height):
        line_parts = []
        for prefix in GRID_PREFIXES:
            current_lines = final_lines[prefix]
            line_parts.append(current_lines[i])

        output_line = GRID_SEPARATOR.join(line_parts)
        print(output_line)

def prepare_external_items(
    items: Iterable[str],
    color_map: Dict[str, str]
) -> List[str]:
    """
    Filter out non-external entries and sort by color, then alphabetically.
    """
    filtered_items = [
        item for item in items
        if not is_grid_definition(item) and not is_e2e_pin_definition(item)
    ]
    return sorted(
        filtered_items,
        key=lambda x: (color_map.get(x, NEUTRAL_BACKGROUND), x.upper())
    )

# --- Main Logic ---

def process_and_output_charts(data_file: str, state_file_bases: List[str]) -> None:
    """
    Main function to load all data, perform global reduction, print results,
    output individual charts, and output consolidated charts for N grids.
    """
    global GRID_PREFIXES, GRID_DIMENSIONS, GLOBAL_CELL_WIDTH, GRID_SEPARATOR, E2E_PINS
    
    # 1. LOAD CONFIGS AND DETERMINE MAX DIMENSIONS
    # E2E_PINS are loaded here
    max_C, max_R, _ = load_all_configs(data_file)
    cell_width = GLOBAL_CELL_WIDTH 

    # 2. GENERATE GRIDS based on specific dimensions and pad to Max R
    grid_lines: Dict[str, List[str]] = {}
    map_coords: Dict[str, Dict[str, Tuple[int, int]]] = {}
    
    for prefix in GRID_PREFIXES:
        C, R = GRID_DIMENSIONS.get(prefix, (max_C, max_R))
        lines, coords = generate_ascii_grid(prefix, C, R, cell_width)
        
        # Pad the generated lines to max_R height
        current_height = len(lines)
        expected_height = (2 * max_R + 1) # Height based on the grid with max_R
        if current_height < expected_height:
             blank_line_len = len(lines[0]) if lines else 0
             blank_line = " " * blank_line_len
             padding_needed = expected_height - current_height
             lines.extend([blank_line] * padding_needed)

        grid_lines[prefix] = lines
        map_coords[prefix] = coords

    # Get the final height (all grids are padded to this)
    if not GRID_PREFIXES:
         print("No grids defined, exiting.")
         return
         
    grid_height = len(grid_lines[GRID_PREFIXES[0]]) 
    
    grid_line_widths: Dict[str, int] = {
        prefix: len(grid_lines[prefix][0]) if grid_lines[prefix] else 0
        for prefix in GRID_PREFIXES
    }
    grid_section_width = sum(grid_line_widths.values()) + ((len(GRID_PREFIXES) - 1) * len(GRID_SEPARATOR))
    
    # 3. LOAD ALL DATA SOURCES (Connections and States)
    initial_data_groups = load_data(data_file)
    initial_state_groups = []
    state_pins_by_prefix: Dict[str, Set[str]] = {}
    
    for prefix, file_base in zip(GRID_PREFIXES, state_file_bases):
        file_path = f"{file_base}.csv"
        initial_state_groups.extend(load_state_data_as_groups(file_path, prefix))
        state_pins_by_prefix[prefix] = load_state_pin_set(file_path, prefix)

    # 4. PERFORM AND PRINT GLOBAL REDUCTION
    print("=" * 70)
    print("PRELIMINARY STEP: GLOBAL CONNECTION GROUP REDUCTION")
    print("=" * 70)

    combined_initial_groups = initial_data_groups + initial_state_groups

    if not combined_initial_groups:
        print("No connection data loaded. Please check data.csv and state files.")
        return

    state_files_str = ', '.join([f"{base}.csv" for base in state_file_bases])
    print(f"--- Original Groups (Combined from data.csv and {state_files_str}): ---")
    for i, group in enumerate(combined_initial_groups):
        print(f"Source Group {i+1}: {', '.join(group)}")

    globally_reduced_groups = reduce_connection_groups(combined_initial_groups)

    print("\n--- Globally Reduced Connection Groups (All Overlaps Merged): ---")
    for i, group in enumerate(globally_reduced_groups):
        print(f"Reduced Group {i+1}: {', '.join(group)}")
    print("=" * 70 + "\n")

    # 5. PERFORM REDUCTION ON data.csv ONLY (for charting Part 1 and Part 2)
    charting_groups_part1 = reduce_connection_groups(initial_data_groups)


    # 6. Part 3 / Part 4 calculation using the new priority logic
    _pin_color_map_part3, external_color_map_part3, consolidated_pin_ops_part3, all_unique_external_items_part3 = \
        calculate_global_colors(globally_reduced_groups, map_coords, state_pins_by_prefix, cell_width)

    # --- Initializing Part 2 variables ---
    pin_color_map_part2: Dict[str, str] = {}
    consolidated_pin_ops_part2: List[Tuple[int, int, str, str]] = []
    external_color_map_part2: Dict[str, str] = {}
    all_unique_external_items_part2: set = set()


    # 7. PART 1: Output Individual Charts 
    print("==================================================================")
    print("PART 1: INDIVIDUAL CONNECTION GROUP CHARTS (FROM data.csv REDUCTION)")
    print("==================================================================")

    color_index: int = 0
    
    # Prepare header template for individual charts
    header_parts = [f"GROUP {p}" for p in GRID_PREFIXES]
    header_str_template = GRID_SEPARATOR.join(header_parts)
    
    for line_data in charting_groups_part1:
        
        is_only_grid_def = all(is_grid_definition(item) for item in line_data)
        if is_only_grid_def and len(line_data) > 0:
            continue

        line_string: str = ",".join(line_data)
        color: str = COLORS[color_index % len(COLORS)]
        color_index += 1

        # --- Prepare Individual Chart Data ---
        non_pin_items: List[str] = []
        color_ops_by_prefix: Dict[str, List[Tuple[int, int, str]]] = {p: [] for p in GRID_PREFIXES}

        for item in line_data:
            if is_pin(item):
                prefix = item[0]
                current_map: Dict[str, Tuple[int, int]] = map_coords[prefix]
                state_pins: set = state_pins_by_prefix.get(prefix, set())

                if item in current_map:
                    r, c_end = current_map[item]
                    c_start = c_end - cell_width
                    text_format_code: str = TEXT_BOLD_ITALIC_STATE if item in state_pins else ""
                    ops_list: List[Tuple[int, int, str]] = color_ops_by_prefix[prefix]
                    ops_list.append((r, c_end, PIN_TERMINATOR))
                    ops_list.append((r, c_start, color + text_format_code))

                    if item not in pin_color_map_part2:
                        pin_color_map_part2[item] = color
                        consolidated_pin_ops_part2.append((r, c_end, PIN_TERMINATOR, prefix))
                        consolidated_pin_ops_part2.append((r, c_start, color + text_format_code, prefix))

            else:
                if not is_grid_definition(item) and not is_e2e_pin_definition(item): 
                    non_pin_items.append(item)
                    if item not in external_color_map_part2:
                        external_color_map_part2[item] = color
                    all_unique_external_items_part2.add(item)

        # --- Format Standalone Cells (Vertically Stacked) ---
        standalone_cells: List[str] = []
        valid_external_items_for_part1 = [item for item in non_pin_items if not is_grid_definition(item) and not is_e2e_pin_definition(item)]
        
        external_cell_width_total = cell_width
        
        if valid_external_items_for_part1:
            border_line: str = "+" + "-" * external_cell_width_total + "+"
            standalone_cells.append(color + border_line + RESET)
            for item in valid_external_items_for_part1:
                standalone_cells.append(color + "|" + item.center(external_cell_width_total) + "|" + RESET)
            standalone_cells.append(color + border_line + RESET)
        
        # --- Output Current Individual Chart ---
        colored_lines_by_prefix: Dict[str, List[str]] = {}
        
        for prefix in GRID_PREFIXES:
            colored_lines = list(grid_lines[prefix])
            apply_coloring(colored_lines, color_ops_by_prefix[prefix])
            colored_lines_by_prefix[prefix] = colored_lines


        pad_cell_width = len(standalone_cells[0]) if standalone_cells else (cell_width + 2) 
        blank_pad_line: str = " " * (pad_cell_width)
        
        standalone_padded: List[str] = standalone_cells + [blank_pad_line] * (grid_height - len(standalone_cells))
        
        # Print Group Header and Separator
        print(f"\n{'-' * (grid_section_width + len(GRID_SEPARATOR) + pad_cell_width)}")
        print(f"Group: {line_string} {color}(COLOR){RESET} (Bold/Italic text = State Active)")
        print(f"{header_str_template.ljust(grid_section_width)}{GRID_SEPARATOR}EXTERNAL")
        
        # Print Rows
        for i in range(grid_height):
            line_parts = [colored_lines_by_prefix[prefix][i] for prefix in GRID_PREFIXES]
            output_line = GRID_SEPARATOR.join(line_parts) + GRID_SEPARATOR + standalone_padded[i]
            print(output_line)

    # 8. PART 2: Output Consolidated Chart (Based on data.csv reduction)
    print("\n\n" + "=" * 80)
    print("PART 2: FINAL CONSOLIDATED CHART (Overlayed Colors from data.csv reduction)")
    print("=" * 80)
    
    final_lines_part2 = build_colored_grid_lines(grid_lines, consolidated_pin_ops_part2)

    # Prepare external items for horizontal table below
    all_external_items_part2 = all_unique_external_items_part2.union(set(E2E_PINS))
    filtered_external_items_part2 = prepare_external_items(all_external_items_part2, external_color_map_part2)
    
    render_switch_grids(
        final_lines_part2,
        grid_height,
        "Note: Bold and italic text indicates pin is active per state file."
    )

    render_external_connections_table(filtered_external_items_part2, external_color_map_part2, cell_width)
    
    print("\n" + "=" * 80)

    # 9. PART 2.5: Output State Interconnection Chart
    print("\n\n" + "=" * 80)
    print("PART 2.5: SWITCH STATE INTERCONNECTIONS (Active Connections from State Files Only)")
    print("=" * 80)
    
    # 1. Reduce the groups that came ONLY from the state files
    state_only_reduced_groups = reduce_connection_groups(initial_state_groups)

    if not state_only_reduced_groups:
        print("No active inter-switch connections detected in the state files.")
    else:
        # 2. Calculate colors and operations based ONLY on state-only groups
        # NOTE: Passing an empty map_coords and state_pins_by_prefix to ensure only pins 
        # that exist in the state file groups get processed for color.
        # We need to reuse the original map_coords and state_pins_by_prefix to place the pins correctly.
        # This reuses the logic of calculate_global_colors but for a subset of groups.
        
        # We define a temporary calculation function to apply colors from state-only groups
        def calculate_state_only_colors(groups, pin_coords_map, state_pins_map, cell_width):
            pin_color_map: Dict[str, str] = {}
            external_color_map: Dict[str, str] = {}
            all_unique_external_items: Set[str] = set()
            consolidated_pin_ops: List[Tuple[int, int, str, str]] = []
            
            group_to_color: Dict[Tuple[str, ...], str] = {}
            # Reset color index for state-only groups
            for i, group in enumerate(groups):
                group_to_color[tuple(group)] = COLORS[i % len(COLORS)] 
                
            # No need for complex sorting here, just iterate
            for group in groups:
                color = group_to_color[tuple(group)]
                for item in group:
                    if is_pin(item):
                        if item not in pin_color_map:
                            pin_color_map[item] = color
                    else:
                        if not is_grid_definition(item) and not is_e2e_pin_definition(item):
                            external_color_map[item] = color
                            all_unique_external_items.add(item) 

            for item, color in pin_color_map.items():
                prefix = item[0]
                if prefix in pin_coords_map:
                    current_map: Dict[str, Tuple[int, int]] = pin_coords_map[prefix]
                    state_pins: Set[str] = state_pins_map.get(prefix, set())

                    if item in current_map:
                        r, c_end = current_map[item]
                        c_start = c_end - cell_width
                        # Pins in this chart are active if they are in the state file
                        text_format_code: str = TEXT_BOLD_ITALIC_STATE if item in state_pins else "" 
                        consolidated_pin_ops.append((r, c_end, PIN_TERMINATOR, prefix))
                        consolidated_pin_ops.append((r, c_start, color + text_format_code, prefix))
                        
            return pin_color_map, external_color_map, consolidated_pin_ops, all_unique_external_items

        _pin_color_map_part2_5, external_color_map_part2_5, consolidated_pin_ops_part2_5, all_unique_external_items_part2_5 = \
            calculate_state_only_colors(state_only_reduced_groups, map_coords, state_pins_by_prefix, cell_width)

        # 3. Generate the Chart
        final_lines_part2_5 = build_colored_grid_lines(grid_lines, consolidated_pin_ops_part2_5)

        # 4. Prepare external items for horizontal table below
        all_external_items_part2_5 = all_unique_external_items_part2_5.union(set(E2E_PINS))
        filtered_external_items_part2_5 = prepare_external_items(all_external_items_part2_5, external_color_map_part2_5)

        # 5. Output the Chart
        render_switch_grids(
            final_lines_part2_5,
            grid_height,
            "Note: Colors represent state-active interconnections only. Bold and italic text indicates pin is active per state file."
        )
        
        # Print horizontal external pins table below
        render_external_connections_table(filtered_external_items_part2_5, external_color_map_part2_5, cell_width)

    # 9. PART 3: Output Consolidated Chart (Based on GLOBAL reduction)
    print("\n\n" + "=" * 80)
    print("PART 3: FINAL CONSOLIDATED CHART (Overlayed Colors from GLOBAL reduction)")
    print("==================================================================")
    
    final_lines_part3 = build_colored_grid_lines(grid_lines, consolidated_pin_ops_part3)

    # Prepare external items for horizontal table below
    all_external_items_part3 = all_unique_external_items_part3.union(set(E2E_PINS))
    filtered_external_items_part3 = prepare_external_items(all_external_items_part3, external_color_map_part3)

    render_switch_grids(
        final_lines_part3,
        grid_height,
        "Note: Bold and italic text indicates pin is active per state file."
    )
    
    # Print horizontal external pins table below
    render_external_connections_table(filtered_external_items_part3, external_color_map_part3, cell_width)
    
    print("\n" + "=" * 80)


    # 10. PART 4: Output E2E Short summary (Dynamically read pins)
    print("\n\n" + "=" * 80)
    print("PART 4: GLOBAL EXTERNAL SHORT SUMMARY (Dynamically Read E2E Pins)")
    print("==================================================================")
    
    e2e_shorts_map: Dict[str, Dict[str, str]] = {pin: {} for pin in E2E_PINS}
    isolated_p_groups: List[Set[str]] = []
    
    for group in globally_reduced_groups:
        group_set = set(group)
        
        # 1. Identify ALL non-switch-pin items in the group (P-elements and E2E pins)
        all_non_pin_items = {
            item for item in group_set 
            if not is_pin(item) and not is_grid_definition(item)
        }
        
        # 2. Separate P-elements for the isolated P-group check
        p_elements_in_group = {item for item in all_non_pin_items if is_p_element(item)}
        
        present_e2e_pins = [pin for pin in E2E_PINS if pin in group_set]

        # --- E2E Shorting Check ---
        if present_e2e_pins:
            for e2e_pin in present_e2e_pins:
                
                # Check for shorts to *any other* non-switch-pin item in the group
                for item in all_non_pin_items:
                    
                    # CRITICAL FIX: Only report the short if the item is *not* the E2E pin itself.
                    if item != e2e_pin: 
                        if item not in e2e_shorts_map[e2e_pin]:
                            # Determine color: P-elements have a color in external_color_map_part3.
                            # Other E2E pins might not, so default to NEUTRAL_BACKGROUND.
                            color = external_color_map_part3.get(item, NEUTRAL_BACKGROUND)
                            e2e_shorts_map[e2e_pin][item] = color

        # --- Isolated P-Group Check ---
        # The group is an isolated P-group if all non-pin items are P-elements
        # AND there are no E2E pins in the group
        is_isolated_p_group = (
            len(p_elements_in_group) == len(all_non_pin_items) and 
            not present_e2e_pins
        )
        
        if is_isolated_p_group and len(p_elements_in_group) > 1:
            isolated_p_groups.append(p_elements_in_group)

    # --- Print E2E shorts ---
    for e2e_pin in E2E_PINS:
        shorted_to = e2e_shorts_map[e2e_pin]
        if shorted_to:
            e2e_line = [f"{e2e_pin} is shorted to: "]
            
            # Sort targets
            sorted_targets = sorted(shorted_to.keys(), key=str.upper)
            
            for item in sorted_targets:
                color = shorted_to[item]
                e2e_line.append(f"{color}( {item} ){RESET} ")
            print("".join(e2e_line))
        else:
            print(f"{e2e_pin} is shorted to: nothing")

    # --- Print Isolated P-Groups ---
    p_group_line = []
    
    printable_isolated_groups = []
    
    # Check if P-groups are truly isolated from E2E pins
    all_e2e_targets = set()
    for target_map in e2e_shorts_map.values():
        all_e2e_targets.update(target_map.keys())
        
    for group in isolated_p_groups:
        # Check if the P-group is shorted to any E2E pin directly
        is_truly_isolated = True
        for item in group:
            if item in all_e2e_targets:
                is_truly_isolated = False
                break
        
        if is_truly_isolated:
            printable_isolated_groups.append(sorted(list(group), key=str.upper))
            
    if printable_isolated_groups:
        p_group_line.append(f"{ISOLATED_LABEL_COLOR}Shorted P-groups:{RESET}")
        for group in printable_isolated_groups:
            p_group_line.append(f" {ISOLATED_LABEL_COLOR}Group:{RESET}")
            for item in group:
                p_group_line.append(f" {ISOLATED_PIN_COLOR}( {item} ){RESET}")
        
    else:
        p_group_line.append(f"{ISOLATED_LABEL_COLOR}Shorted P-groups:{RESET} none")

    print("".join(p_group_line))

    print("\n" + "=" * 80)
    
# --- Execution ---
if __name__ == '__main__':
    data_file = 'data.csv'
    script_name = sys.argv[0].split('/')[-1]
    
    # 1. Read data.csv and determine the number of defined grids (N)
    try:
        _, _, GRID_PREFIXES_FINAL = load_all_configs(data_file) 
    except Exception as e:
        print(f"FATAL ERROR during config loading: {e}")
        sys.exit(1)
        
    expected_args = len(GRID_PREFIXES_FINAL)
    
    # All arguments after the script name are the state file bases
    state_file_bases = sys.argv[1:]
    received_args = len(state_file_bases)
    
    # 2. Check for parameter mismatch
    if received_args != expected_args:
        
        if expected_args == 0:
            print("\nERROR: No grid definitions (X:CxR) found in data.csv. Cannot proceed.")
        else:
            # 3. Display error and how to solve
            print("\n" + "=" * 70)
            print("INPUT ERROR: State file mismatch.")
            print("=" * 70)
            
            print(f"Number of grids defined in 'data.csv': {expected_args}")
            print(f"Prefixes found: {', '.join(GRID_PREFIXES_FINAL)}")
            print(f"Number of state file bases provided: {received_args}")
            
            # Construct the example usage
            example_bases = ['state1', 'state2', 'state3', 'state4'][:expected_args]
            
            if expected_args > 0:
                 example_command = [f"<base_for_{p}>" for p in GRID_PREFIXES_FINAL]
                 print(f"\nUsage: python {script_name} {' '.join(example_command)}")
                 print(f"Example: python {script_name} {' '.join(example_bases)}")
            else:
                 print("\nNo grids were defined in data.csv (e.g., A:3x4). Please add definitions.")
                 
            print("=" * 70)
        sys.exit(1)

    # 4. If match, proceed with drawing grids
    print(f"\nINFO: Matched {expected_args} defined grids ({', '.join(GRID_PREFIXES_FINAL)}) to {received_args} state files. Starting chart generation...")
    
    # Print the dynamically loaded E2E pins for confirmation
    print(f"INFO: Dynamically loaded E2E Pins for Part 4 summary: {', '.join(E2E_PINS)}")
    
    process_and_output_charts(data_file, state_file_bases)
