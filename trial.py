from faker_events import Event, EventGenerator
from faker import Faker

faker = Faker()

customer = {'Name': 'Unknown', 'Job': None, 'Created': None, 'Updated': None}

def new_customer(event, profile):
    return {
        "Name": profile.first_name,
        "Job": profile.job,
        "Created": event.time,
        "Updated": event.time
    }

def change_job(event, profile):
    return {
        "Job": faker.job(),
        "Updated": event.time
    }

new_customer_event = Event(customer, new_customer)
customer_marriged_event = Event(customer, change_job)

new_customer_event >> customer_marriged_event

EventGenerator.set_first_events(new_customer_event)
