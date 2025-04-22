import sqlite3

# Connect to the database
conn = sqlite3.connect('hospital.db')
cursor = conn.cursor()

try:
    # Define the appointment IDs to delete
    appointment_ids_to_delete = (1,2)

    # Delete from appointments table
    cursor.execute("""
        DELETE FROM appointments
        WHERE appointment_id IN (?, ?)
    """, appointment_ids_to_delete)

    conn.commit()
    print("✅ Successfully deleted appointment records with IDs 6 and 8.")
except Exception as e:
    print("❌ Error while deleting appointment records:", e)
finally:
    conn.close()
