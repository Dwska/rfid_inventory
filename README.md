To run the project you need to install these library:
pip install -r requirements.txt

After that, Run these commands:
# 1. Apply migrations (creates the DB tables)
python manage.py makemigrations inventory
python manage.py migrate

# 2. Create a Django superuser (for /admin/)
python manage.py createsuperuser

# 3. Seed the database with sample products and RFID users
python manage.py seed

# 4. Start the development server
python manage.py runserver
