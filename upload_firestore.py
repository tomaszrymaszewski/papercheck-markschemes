import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json

# Fetch the service account key JSON file contents
cred = credentials.Certificate('g-cloud/papercheck-2e43e-firebase-adminsdk-fbsvc-e46a7adb79.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred)

db = firestore.client()

def upload_json_to_firestore_from_file(filepath):
    """Uploads JSON objects from a file to Firestore.

    Args:
        filepath: Path to the JSON file.  File should contain a JSON array of objects.
    """
    try:
        with open(filepath, 'r') as f:
            json_array = json.load(f)

        if not isinstance(json_array, list):
            raise ValueError("The JSON file must contain a JSON array.")

        for json_object in json_array:
            try:
                #  Assumes each object in the array has a 'docId' key for the document ID.
                #  If this isn't your format, change the next line accordingly.
                document_id = json_object['docId']

                # Check for valid document ID (string and valid Python identifier).
                if not isinstance(document_id, str) or not document_id.isidentifier():
                    raise ValueError(f"Invalid document ID '{document_id}' in JSON object. Document IDs must be strings and valid Python identifiers.")

                doc_ref = db.collection('mark-schemes').document(document_id)
                # Remove the 'docId' key before setting the document.
                del json_object['docId']
                doc_ref.set(json_object)
                print(f"Document {document_id} successfully written to 'mark-schemes' collection.")
            except KeyError:
                print("Error: JSON object must contain a 'docId' key for the document ID.")
            except firestore.exceptions.FirestoreException as e:
                print(f"Firestore error for document {document_id}: {e}")
            except ValueError as e:
                print(f"Value Error for document {document_id}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred for document {document_id}: {e}")

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file {filepath}")
    except ValueError as e:
        print(f"Value Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# Example usage: Replace 'data.json' with the actual path to your JSON file.
upload_json_to_firestore_from_file('data/tailored.json')

# Clean up (optional, but good practice).
firebase_admin.delete_app(firebase_admin.get_app())
