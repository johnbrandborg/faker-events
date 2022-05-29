"""
Kafka Consumer to Console
"""

import sys

from kafka import KafkaConsumer


def main():
    consumer = KafkaConsumer('test', bootstrap_servers='kafka', group_id='c1')

    for msg in consumer:
        print(msg)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as error:
        print("\nExiting.", error, file=sys.stderr)
