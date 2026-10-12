import pandas as pd
"Complete thes functions or write your own to perform the following tasks"

def calculate_profit_by_order(orders_df):
    """Calculate profit for each order."""

    orders_df = orders_df.copy()

    orders_df["Profit"] = (
        orders_df["List Price"]
        * (1 - orders_df["Discount Percent"] / 100)
        - orders_df["cost price"]
    ) * orders_df["Quantity"]

    return orders_df

def calculate_most_profitable_region(orders_df):
    """Find the region with the highest total profit."""

    region_profit = (
        orders_df.groupby("Region")["Profit"]
        .sum()
    )

    most_profitable_region = region_profit.idxmax()
    highest_profit = region_profit.max()

    return most_profitable_region, highest_profit

def find_most_common_ship_method(orders_df):
    """Find the most frequently used shipping method per category."""

    ship_counts = (
        orders_df.groupby(["Category", "Ship Mode"])
        .size()
        .reset_index(name="Order Count")
    )

    most_common = (
        ship_counts.sort_values(
            ["Category", "Order Count", "Ship Mode"],
            ascending=[True, False, True]
        )
        .drop_duplicates(subset=["Category"])
        .reset_index(drop=True)
    )

    return most_common

def find_number_of_order_per_category(orders_df):
    """Count orders by category and sub-category."""

    order_counts = (
        orders_df.groupby(["Category", "Sub Category"])["Order Id"]
        .nunique()
        .reset_index(name="Order Count")
    )

    return order_counts
