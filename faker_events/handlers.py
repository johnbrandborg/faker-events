"""
Stream handlers for sending messages
"""

import boto3
from kafka import KafkaProducer

__all__ = ['Stream']


class Stream():
    """
    A Handler for sending events to a Data Steam. By default events are printed

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
            self.send = print
        elif stype == 'kafka':
            self.send = self._setup_kafka()
        elif stype == 'kinesis':
            self.send = self._setup_kinesis()
        else:
            raise ValueError('Unknown stream type')

    def _setup_kafka(self) -> object:
        if self.host is None:
            raise ValueError('A host name  must be supplied with Kafka')

        if self.name is None:
            raise ValueError('A stream "name" must be supplied with kinesis')

        producer = KafkaProducer(bootstrap_servers=[self.host])

        def send(message):
            producer.send(topic=self.name, value=message.encode())

        return send

    def _setup_kinesis(self) -> object:
        if self.name is None:
            raise ValueError('A stream "name" must be supplied with kinesis')

        if self.key is None:
            raise ValueError('A partition key must be supplied with Kinesis')

        kinesis = boto3.client('kinesis')

        def send(message):
            kinesis.put_record(
                StreamName=self.name,
                Data=message.encode(),
                PartitionKey=self.key,
            )

        return send
