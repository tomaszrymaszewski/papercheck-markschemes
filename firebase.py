import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

cred = credentials.Certificate("g-cloud/papercheck-2e43e-firebase-adminsdk-fbsvc-e46a7adb79.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def import_json(file_path):
    print(f"Attempting to import JSON from: {file_path}")
    print(f"Current working directory: {os.getcwd()}")

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"JSON data loaded successfully: {data}")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return

    for collection_name, collection_data in data.items():
        collection_name = collection_name.replace("_", " ").replace(" MS", "")
        print(f"Processing document: {collection_name}") #now using collection name as document name.
        document_ref = db.collection("mark-schemes").document(collection_name) #using "Questions" as the collection.
        try:
            if isinstance(collection_data, dict):
                document_ref.set(collection_data)
                print(f"Document {collection_name} added to collection Questions.")
            else:
                print(f"Warning: Document {collection_name} is not a dictionary. Skipping.")
        except Exception as e:
            print(f"Error adding document {collection_name} to collection Questions: {e}")

    print("Import process completed.")


import_json('output_directory/joint_mark_schemes.json')
