from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)
client = MongoClient(os.environ.get("MONGO_URI"))
db = client['subscriptiondb']
subsCollection = db['subscriptions']
subtypesCollection = db['subscriptiontypes']

def initialize_subscription_types():
    if subtypesCollection.find_one({"id": 1}):
        return
    subscription_type = {
        "id": 1,
        "name": "Basic",
        "price": 99,
        "description": "Watch all on demand videos"
    }
    subtypesCollection.insert_one(subscription_type)

@app.route('/')
def index():
    return 'Welcome to the Subscriptions API!'

# Get all subscription types
@app.route("/subscriptiontypes", methods=["GET"])
def get_subscription_types():
    subscription_types = list(subtypesCollection.find({}, {"_id": 0}))
    return jsonify(subscription_types), 200

# Create a new subscription
@app.route("/subscriptions", methods=["POST"])
def create_subscription():
    user_id = request.json.get("user_id", None)
    subscription_type_id = request.json.get("subscription_type_id", None)

    # Validate user ID and subscription type ID
    if not user_id or not subscription_type_id:
        return jsonify({"msg": "Missing user ID or subscription type ID"}), 400

    subscription_type = subtypesCollection.find_one({"id": subscription_type_id})
    if not subscription_type:
        return jsonify({"msg": "Subscription type not found"}), 404
    
    # Check if user already has an active subscription
    now = datetime.utcnow()
    existing_subscription = subsCollection.find_one({"user_id": user_id, "expiration_date": {"$gt": now}})
    if existing_subscription:
        return jsonify({"msg": "User already has an active subscription"}), 409
    # Calculate expiration date
    days_valid = 30
    expiration_date = now + timedelta(days=days_valid)

    # Create new subscription
    subscription = {
        "user_id": user_id,
        "subscription_type_id": subscription_type_id,
        "expiration_date": expiration_date
    }
    subsCollection.insert_one(subscription)

    return jsonify({"msg": "Subscription created"}), 201

# Check if a user has an active subscription
@app.route("/subscriptions/<user_id>/active", methods=["GET"])
def check_subscription(user_id):
    now = datetime.utcnow()

    subscription = subsCollection.find_one({"user_id": user_id, "expiration_date": {"$gt": now}})
    if not subscription:
        return jsonify({"msg": "User does not have an active subscription"}), 404

    return jsonify({"msg": "User has an active subscription"}), 200

# Cancel a subscription
@app.route("/subscriptions/<user_id>/cancel", methods=["PUT"])
def cancel_subscription(user_id):
    # Query for user's active subscription
    now = datetime.utcnow()
    subscription = subsCollection.find_one({"user_id": user_id, "expiration_date": {"$gt": now}})

    if not subscription:
        return jsonify({"msg": "User does not have an active subscription"}), 404

    # Update the subscription expiration date to now, effectively canceling it
    subsCollection.update_one({"_id": subscription["_id"]}, {"$set": {"expiration_date": now}})

    return jsonify({"msg": "Subscription has been cancelled"}), 200


initialize_subscription_types()

if __name__ == '__main__':
    app.run(debug=True, ssl_context=None)
