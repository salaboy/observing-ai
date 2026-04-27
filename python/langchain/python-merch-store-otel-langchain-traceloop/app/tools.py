import json
import uuid
from collections import Counter

from langchain_core.tools import tool

from app.inventory import INVENTORY


@tool
def get_item_stock(item_name: str) -> str:
    """Get the stock quantity and price of a Python merch item
    by project name and/or type (T-Shirt, Socks, Sticker)."""
    query = item_name.lower()
    matches = [
        item for item in INVENTORY
        if query in item.display_name.lower()
        or query in item.project_name.lower()
        or query in item.type.lower()
    ]

    if not matches:
        return f"No merch found matching '{item_name}'"

    lines = [
        f"- {item.display_name}: {item.quantity} units in stock at ${item.price:.2f} (logo: {item.logo_url})"
        for item in matches
    ]
    return "\n".join(lines)


@tool
def display_merch_images(query: str) -> str:
    """Display visual product cards for Python merch items with their project logos
    in the UI. Pass a project name (e.g. 'NumPy'), a type (e.g. 'T-Shirt', 'Socks',
    'Sticker'), or 'all' to show everything."""
    if query.strip().lower() == "all":
        items = INVENTORY
    else:
        q = query.lower()
        items = [
            item for item in INVENTORY
            if q in item.display_name.lower()
            or q in item.project_name.lower()
            or q in item.type.lower()
        ]

    json_items = [
        {
            "projectName": item.project_name,
            "type": item.type,
            "price": item.price,
            "stock": item.quantity,
            "logoUrl": item.logo_url,
        }
        for item in items
    ]
    return f"<merch-items>{json.dumps(json_items)}</merch-items>"


@tool
def place_order(items: list[dict[str, str | int]]) -> str:
    """Place a confirmed order for one or more Python merch items. Call this only
    after the user has explicitly confirmed they want to place the order. Each item
    must include project_name, type (T-Shirt, Socks, or Sticker), and quantity."""
    ordered_items = []
    total = 0.0
    not_found = []

    for line in items:
        project_name = line.get("project_name", "")
        item_type = line.get("type", "")
        quantity = line.get("quantity", 1)

        match = next(
            (inv for inv in INVENTORY
             if inv.project_name.lower() == project_name.lower()
             and inv.type.lower() == item_type.lower()),
            None,
        )

        if match is None:
            not_found.append(f"{project_name} {item_type}")
            continue

        for _ in range(quantity):
            ordered_items.append(match)
        total += match.price * quantity

    if not_found:
        return (
            "Could not place order — the following items were not found in the catalog: "
            + ", ".join(not_found)
        )

    order_id = uuid.uuid4().hex[:8].upper()

    counts = Counter(item.display_name for item in ordered_items)
    items_str = ", ".join(f"{count}x {name}" for name, count in counts.items())

    return (
        f"Your order #{order_id} has been placed successfully! \U0001f389\n"
        f"Items: {items_str}\n"
        f"Total: ${total:.2f}\n"
        f"It will be shipped to you as soon as possible. Thank you for shopping at the Python Merch Store!"
    )


@tool
def list_all_items() -> str:
    """List all available Python project merch items (T-Shirts, Socks, Stickers)
    with their quantities and prices."""
    lines = ["Current Python merch inventory:"]
    current_project = ""
    for item in INVENTORY:
        if item.project_name != current_project:
            current_project = item.project_name
            lines.append(f"\n{current_project} ({item.logo_url})")
        lines.append(f"  - {item.type}: {item.quantity} units at ${item.price:.2f}")
    return "\n".join(lines)
