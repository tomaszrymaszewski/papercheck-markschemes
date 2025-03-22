import firebase_admin
from firebase_admin import credentials, firestore
import os

# Replace with your service account key file path
cred = credentials.Certificate("g-cloud/papercheck-2e43e-firebase-adminsdk-fbsvc-e46a7adb79.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def delete_collection(coll_ref, batch_size):
    docs = coll_ref.stream()  # Removed page_size
    deleted = 0
    for doc in docs:
        print(f"Deleting document: {doc.id} from collection {coll_ref.id}")
        doc.delete()
        deleted += 1
    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

def delete_all_collections(db):
    collections = db.collections()
    for collection in collections:
        try:
            delete_collection(collection, 100)
            print(f"Collection '{collection.id}' deleted successfully.")
        except Exception as e:
            print(f"An error occurred deleting collection '{collection.id}': {e}")

try:
    delete_all_collections(db)
    print("All collections deleted (potentially).")
except Exception as e:
    print(f"A major error occurred: {e}")

firebase_admin.delete_app(firebase_admin.get_app())

