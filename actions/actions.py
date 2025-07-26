import json
import sqlite3
import datetime as dt
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    SlotSet,
    EventType,
    SessionStarted,
    ActionExecuted,
)

DB = "store.db"

# Utility function to run SQL queries
def run_query(q, params=(), one=False):
    with sqlite3.connect(DB) as conn:
        cur = conn.execute(q, params)
        res = cur.fetchone() if one else cur.fetchall()
    return res
def get_inventory():
    data = run_query("SELECT name, qty FROM inventory")
    return {item[0]: item[1] for item in data}

# Session start (important fix)
class ActionSessionStart(Action):
    def name(self) -> str:
        return "action_session_start"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        dispatcher.utter_message(text="Hello there! Welcome to the Green Basket🧺! How can I help you?")
        return [SessionStarted(), ActionExecuted("action_listen")]

# Fetch inventory
class ActionFetchInventory(Action):
    def name(self) -> Text:
        return "action_fetch_inventory"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        inventory = get_inventory()  
        if not inventory:
            dispatcher.utter_message(text="❌ Inventory is currently unavailable.")
        else:
            message = "🧺 Available vegetables:\n"
            for veg, qty in inventory.items():
                message += f"• {veg} ({qty} kg)\n"
            dispatcher.utter_message(text=message)
        return []


class ActionGetPrice(Action):
    def name(self) -> Text:
        return "action_get_price"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        veg_item = tracker.get_slot("veg_item")
        print(f"DEBUG: veg_item = {veg_item}") 

        if not veg_item:
            dispatcher.utter_message(text="❗Please tell me which vegetable you want the price for.")
            return []

        data = run_query("SELECT unit_price FROM inventory WHERE name = ?", (veg_item,))
        
        if data:
            price = data[0][0]
            dispatcher.utter_message(text=f"💲 The price of {veg_item} is ₹{price} per kg.")
        else:
            dispatcher.utter_message(text=f"❌ Sorry, I couldn't find the price for {veg_item}.")

        return []




# Add or update order
class ActionAddOrder(Action):
    def name(self) -> Text:
        return "action_add_order"

    def run(self, dispatcher, tracker, domain):
        veg = tracker.get_slot("veg_item")
        qty = tracker.get_slot("veg_qty")
        order_list = tracker.get_slot("order_list") or []

        if veg and qty:
            price_result = run_query("SELECT price FROM inventory WHERE name = ?", (veg,), one=True)
            if price_result:
                price_per_kg = price_result[0]
                total_price = qty * price_per_kg
                order_list.append({"item": veg, "qty": qty, "price": total_price})
                dispatcher.utter_message(
                    text=f"🛒 Added {qty} kg of {veg} (₹{total_price}) to your order.\n➕ Do you want to add anything else or proceed to payment?"
                )
                return [SlotSet("order_list", order_list), SlotSet("veg_item", None), SlotSet("veg_qty", None)]
            else:
                dispatcher.utter_message(text="❌ Sorry, that item is not available.")
        else:
            dispatcher.utter_message(text="Please specify the vegetable and quantity.")
        return []

# Show order summary
class ActionShowOrderSummary(Action):
    def name(self) -> Text:
        return "action_show_order_summary"

    def run(self, dispatcher, tracker, domain):
        orders = tracker.get_slot("order_list") or []
        if not orders:
            dispatcher.utter_message(text="🛒 Your cart is empty.")
            return []

        msg = "📦 Your Order Summary:\n"
        total = 0
        for o in orders:
            msg += f"- {o['item']} - {o['qty']} kg - ₹{o['price']}\n"
            total += o['price']
        msg += f"\n💰 Total: ₹{total}"
        dispatcher.utter_message(text=msg)
        return []

# Save order to database
class ActionSaveOrder(Action):
    def name(self) -> Text:
        return "action_save_order"

    def run(self, dispatcher, tracker, domain):
        name = tracker.get_slot("name")
        phone = tracker.get_slot("phone")
        address = tracker.get_slot("address")
        orders = tracker.get_slot("order_list") or []

        # if not orders:
        #     dispatcher.utter_message(text="No items in order to save.")
        #     return []

        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_data = json.dumps(orders)

        run_query(
            "INSERT INTO orders (name, phone, address, order_details, datetime) VALUES (?, ?, ?, ?, ?)",
            (name, phone, address, order_data, now)
        )

        dispatcher.utter_message(text="💾 Your order has been saved successfully.")
        return [SlotSet("checkout_completed", True)]

# Confirm payment
class ActionProceedPayment(Action):
    def name(self) -> Text:
        return "action_proceed_payment"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(text="💳 Payment received. ✅ Order confirmed!")
        return []

# Cancel order
class ActionCancelOrder(Action):
    def name(self) -> Text:
        return "action_cancel_order"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(text="🗑️ Your order has been cancelled.")
        return [
            SlotSet("veg_item", None),
            SlotSet("veg_qty", None),
            SlotSet("order_list", None),
            SlotSet("name", None),
            SlotSet("phone", None),
            SlotSet("address", None),
            SlotSet("checkout_completed", None),
        ]

# Validate checkout form
class ValidateCheckoutForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_checkout_form"

    def validate_name(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> Dict:
        if len(slot_value) >= 2:
            return {"name": slot_value}
        dispatcher.utter_message(text="❗ Please enter a valid name.")
        return {"name": None}

    def validate_phone(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> Dict:
        if slot_value.isdigit() and len(slot_value) == 10:
            return {"phone": slot_value}
        dispatcher.utter_message(text="❗ Please enter a valid 10-digit phone number.")
        return {"phone": None}

    def validate_address(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> Dict:
        if len(slot_value) > 5:
            return {"address": slot_value}
        dispatcher.utter_message(text="❗ Address must be more descriptive.")
        return {"address": None}
