"""
Kafka Consumer to Console
"""

from kafka import KafkaConsumer

consumer = KafkaConsumer('test', bootstrap_servers='kafka', group_id='c1')

for msg in consumer:
    print(msg)
