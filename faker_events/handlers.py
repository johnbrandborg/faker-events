"""
Stream handlers for sending messages
"""

import json
from sys import stdout

from .text_color import eprint, Palatte

__all__ = ['Stream']


class Stream():
    """
    A Handler for sending events to a Data Steam. By default events are writen
    to standard out on the console.

    Parameters
    ----------
        stype: str
            Stream Type. 'console', 'kafka' or 'kinesis'
        host: str
            Host to connect too (Used for Kafka)
        name: str
            Topic Name for Kafka or Stream Name for Kinesis
        key: str
            Partition Key to be used.  (Required for Kinesis)
    """

    def __init__(self,
                 stype: str = 'console',
                 host: str = None,
                 name: str = None,
                 key: str = None):
        self.stype = stype
        self.host = host
        self.name = name
        self.key = key

        if stype == 'console':
            self._setup_console()
        elif stype == 'kafka':
            self._setup_kafka()
        elif stype == 'kinesis':
            self._setup_kinesis()
        else:
            raise ValueError('Unknown stream type')

    def _setup_console(self):
        def send(message):
            stdout.write(json.dumps(message) + '\n')
        self.send = send

    def _setup_kafka(self) -> None:
        eprint("Logging to Kafka", Palatte.BLUE)
        if self.host is None:
            raise ValueError('A host name  must be supplied with Kafka')

        if self.name is None:
            raise ValueError('A stream "name" must be supplied with kinesis')

        from kafka import KafkaProducer
        producer = KafkaProducer(
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            bootstrap_servers=[self.host])

        def send_kafka(message):
            producer.send(topic=self.name, value=message)
        self.send = send_kafka

    def _setup_kinesis(self):
        eprint("Logging to Kinesis", Palatte.BLUE)
        if self.name is None:
            raise ValueError('A stream "name" must be supplied with kinesis')

        if self.key is None:
            raise ValueError('A partition key must be supplied with Kinesis')

        import boto3
        kinesis = boto3.client('kinesis')

        def send(message):
            formatted = json.dumps(message).encode()
            kinesis.put_record(
                StreamName=self.name,
                Data=formatted,
                PartitionKey=self.key,
            )
        self.send = send
