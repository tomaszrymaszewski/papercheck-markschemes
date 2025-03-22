import firebase_admin
from firebase_admin import firestore
import json
import os

# Initialize Firebase (replace with your service account credentials)
cred = firebase_admin.credentials.Certificate("g-cloud/papercheck-2e43e-firebase-adminsdk-fbsvc-e46a7adb79.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def download_all_firestore_to_single_json(output_filename="output_directory/all_firestore_data.json"):
    """Downloads all collections from Firestore into a single JSON file."""

    try:
        all_data = {}  # Dictionary to hold data for all collections

        collections = db.collections()
        for collection_ref in collections:
            collection_name = collection_ref.id
            all_docs = []
            docs = collection_ref.stream()
            for doc in docs:
                all_docs.append(doc.to_dict())
            all_data[collection_name] = all_docs

        # Create the output directory if it doesn't exist.
        output_dir = os.path.dirname(output_filename)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_filename, "w") as f:
            json.dump(all_data, f, indent=4)
        print(f"All Firestore data saved to '{output_filename}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

# Example Usage:
download_all_firestore_to_single_json() #This will create output_directory if it doesn't already exist.

