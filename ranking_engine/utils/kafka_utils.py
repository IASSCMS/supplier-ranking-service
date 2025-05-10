"""
Kafka utilities for the Supplier Ranking Service

This module provides Kafka client functionality for producing and consuming
messages related to supplier events and ranking updates.
"""

import json
import logging
import threading
import time
from typing import Dict, List, Any, Callable, Optional

from kafka import KafkaConsumer, KafkaProducer
from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaClient:
    """
    Client for interacting with Kafka for the Supplier Ranking Service.
    Handles producing events to Kafka topics and consuming events from Kafka topics.
    """

    def __init__(self):
        """Initialize Kafka producer and consumer"""
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer = None
        self._consumers = {}
        self._running = False
        self._consumer_threads = {}

    @property
    def producer(self) -> Optional[KafkaProducer]:
        """
        Lazy initialization of Kafka producer.
        Returns:
            KafkaProducer: Configured Kafka producer instance or None if initialization fails
        """
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                    acks='all',  # Wait for all replicas to acknowledge
                    retries=3,   # Retry sending messages up to 3 times
                    retry_backoff_ms=500  # Wait 500ms between retries
                )
                logger.info(f"Kafka producer initialized with servers: {self.bootstrap_servers}")
            except Exception as e:
                logger.error(f"Failed to create Kafka producer: {str(e)}")
                self._producer = None
        return self._producer

    def get_consumer(self, topic: str, group_id: str) -> Optional[KafkaConsumer]:
        """
        Get or create a consumer for a specific topic and group.
        
        Args:
            topic: The Kafka topic to consume from
            group_id: The consumer group ID
            
        Returns:
            KafkaConsumer: Configured Kafka consumer instance or None if initialization fails
        """
        consumer_key = f"{topic}_{group_id}"
        if consumer_key not in self._consumers:
            try:
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=group_id,
                    auto_offset_reset='earliest',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    key_deserializer=lambda x: x.decode('utf-8') if x else None,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,  # Commit offsets every 5 seconds
                    session_timeout_ms=30000,  # Timeout if no heartbeat in 30 seconds
                    heartbeat_interval_ms=10000  # Heartbeat every 10 seconds
                )
                self._consumers[consumer_key] = consumer
                logger.info(f"Kafka consumer created for topic {topic}, group {group_id}")
            except Exception as e:
                logger.error(f"Failed to create Kafka consumer for topic {topic}: {str(e)}")
                return None
        return self._consumers[consumer_key]

    def publish_event(self, topic: str, event_type: str, payload: Dict[str, Any], key: str = None) -> bool:
        """
        Publish an event to a Kafka topic.
        
        Args:
            topic: Kafka topic to publish to
            event_type: Type of event being published
            payload: Event data to publish
            key: Optional message key for partitioning
            
        Returns:
            bool: True if publishing was successful, False otherwise
        """
        if self.producer is None:
            logger.error("Kafka producer not initialized - cannot publish event")
            return False

        message = {
            'event_type': event_type,
            'timestamp': int(time.time() * 1000),
            'payload': payload,
            'source': 'supplier_ranking_service'
        }

        try:
            future = self.producer.send(topic, key=key, value=message)
            future.get(timeout=10)  # Wait for the send to complete
            logger.info(f"Published event {event_type} to topic {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event to Kafka topic {topic}: {str(e)}")
            return False

    def subscribe(self, topic: str, group_id: str, callback: Callable[[Dict[str, Any], Optional[str]], None]) -> bool:
        """
        Subscribe to a topic and process messages with a callback.
        
        Args:
            topic: Kafka topic to subscribe to
            group_id: Consumer group ID
            callback: Function to call with each message (takes message value and key as parameters)
            
        Returns:
            bool: True if subscription was successful, False otherwise
        """
        consumer = self.get_consumer(topic, group_id)
        if not consumer:
            logger.error(f"Failed to subscribe to topic {topic}: consumer could not be created")
            return False

        def consumer_thread():
            logger.info(f"Starting consumer for topic {topic}, group {group_id}")
            try:
                for message in consumer:
                    if not self._running:
                        break
                    try:
                        logger.debug(f"Received message from {topic}: {message.value}")
                        callback(message.value, message.key)
                    except Exception as e:
                        logger.error(f"Error processing Kafka message: {str(e)}")
            except Exception as e:
                logger.error(f"Consumer error for topic {topic}: {str(e)}")
            finally:
                try:
                    consumer.close()
                    logger.info(f"Consumer for topic {topic}, group {group_id} stopped")
                except Exception as e:
                    logger.error(f"Error closing consumer: {str(e)}")

        thread_key = f"{topic}_{group_id}"
        self._consumer_threads[thread_key] = threading.Thread(
            target=consumer_thread,
            name=f"kafka-consumer-{topic}-{group_id}"
        )
        self._consumer_threads[thread_key].daemon = True
        logger.info(f"Created consumer thread for topic {topic}, group {group_id}")
        return True

    def start(self) -> None:
        """Start all consumers"""
        self._running = True
        for thread_key, thread in self._consumer_threads.items():
            if not thread.is_alive():
                thread.start()
                logger.info(f"Started consumer thread: {thread_key}")
        logger.info("Kafka client started")

    def stop(self) -> None:
        """Stop all consumers and producer"""
        logger.info("Stopping Kafka client...")
        self._running = False
        
        # Stop consumer threads
        for thread_key, thread in self._consumer_threads.items():
            if thread.is_alive():
                logger.info(f"Joining thread {thread_key}")
                thread.join(timeout=5)
                if thread.is_alive():
                    logger.warning(f"Thread {thread_key} did not terminate gracefully")
        
        # Close consumers
        for consumer_key, consumer in self._consumers.items():
            try:
                logger.info(f"Closing consumer {consumer_key}")
                consumer.close()
            except Exception as e:
                logger.error(f"Error closing consumer {consumer_key}: {str(e)}")
        
        # Clear collections
        self._consumers = {}
        self._consumer_threads = {}
        
        # Close producer
        if self._producer:
            try:
                logger.info("Closing Kafka producer")
                self._producer.close()
                self._producer = None
            except Exception as e:
                logger.error(f"Error closing producer: {str(e)}")
        
        logger.info("Kafka client stopped")


# Singleton instance
kafka_client = KafkaClient()


class SupplierEventConsumer:
    """
    Consumer for supplier events from the Auth Service.
    Handles events related to supplier creation, updates, and deletion.
    """

    def __init__(self):
        """Initialize consumer with topic and group ID from settings"""
        self.topic = settings.KAFKA_SUPPLIER_EVENTS_TOPIC
        self.group_id = settings.KAFKA_CONSUMER_GROUP_ID
        
    def start(self) -> bool:
        """
        Start consuming supplier events from Kafka.
        
        Returns:
            bool: True if consumer started successfully, False otherwise
        """
        success = kafka_client.subscribe(
            self.topic,
            self.group_id,
            self._process_supplier_event
        )
        if success:
            kafka_client.start()
            logger.info(f"Started supplier event consumer on topic {self.topic}")
            return True
        logger.error(f"Failed to start supplier event consumer on topic {self.topic}")
        return False

    def _process_supplier_event(self, event: Dict[str, Any], key: Optional[str]) -> None:
        """
        Process a supplier event from Kafka.
        
        Args:
            event: The event data including type and payload
            key: Optional message key
        """
        event_type = event.get('event_type')
        payload = event.get('payload', {})
        
        if not event_type or not payload:
            logger.warning(f"Received invalid supplier event: {event}")
            return
        
        logger.info(f"Processing supplier event: {event_type}")
        
        # Import here to avoid circular imports
        from ranking_engine.services.supplier_service import update_supplier_cache
        
        try:
            if event_type == 'supplier_created':
                supplier_id = payload.get('id')
                if supplier_id:
                    logger.info(f"Processing supplier created event for supplier {supplier_id}")
                    update_supplier_cache(supplier_id)
            elif event_type == 'supplier_updated':
                supplier_id = payload.get('id')
                if supplier_id:
                    logger.info(f"Processing supplier updated event for supplier {supplier_id}")
                    update_supplier_cache(supplier_id)
            elif event_type == 'supplier_deleted':
                supplier_id = payload.get('id')
                if supplier_id:
                    logger.info(f"Processing supplier deleted event for supplier {supplier_id}")
                    # Implement deletion logic if needed
                    pass
            else:
                logger.warning(f"Unknown event type: {event_type}")
        except Exception as e:
            logger.error(f"Error handling supplier event: {str(e)}")


class RankingEventProducer:
    """
    Producer for ranking events.
    Publishes events related to supplier ranking updates and batch completions.
    """

    def __init__(self):
        """Initialize producer with topic from settings"""
        self.topic = settings.KAFKA_RANKING_EVENTS_TOPIC
        
    def publish_ranking_update(self, supplier_id: int, ranking_data: Dict[str, Any]) -> bool:
        """
        Publish a ranking update event.
        
        Args:
            supplier_id: ID of the supplier whose ranking was updated
            ranking_data: The updated ranking data
            
        Returns:
            bool: True if publishing was successful, False otherwise
        """
        logger.info(f"Publishing ranking update for supplier {supplier_id}")
        return kafka_client.publish_event(
            self.topic,
            'ranking_updated',
            {
                'supplier_id': supplier_id,
                'ranking': ranking_data,
                'timestamp': int(time.time() * 1000)
            },
            key=str(supplier_id)
        )
        
    def publish_ranking_batch_complete(self, date: str, count: int, summary: Dict[str, Any] = None) -> bool:
        """
        Publish event when a batch ranking is complete.
        
        Args:
            date: The date the batch ranking was completed for
            count: Number of suppliers ranked in the batch
            summary: Optional summary data about the batch
            
        Returns:
            bool: True if publishing was successful, False otherwise
        """
        logger.info(f"Publishing ranking batch completion for date {date}, {count} suppliers ranked")
        payload = {
            'date': str(date),
            'supplier_count': count
        }
        
        if summary:
            payload['summary'] = summary
            
        return kafka_client.publish_event(
            self.topic,
            'ranking_batch_complete',
            payload
        )


class IntegrationEventProducer:
    """
    Producer for integration events with other microservices.
    Publishes events that other services might be interested in.
    """
    
    def __init__(self):
        """Initialize producer with topic from settings"""
        self.topic = settings.KAFKA_INTEGRATION_EVENTS_TOPIC
        
    def publish_quality_issue_detected(self, supplier_id: int, quality_data: Dict[str, Any]) -> bool:
        """
        Publish an event when a quality issue is detected.
        
        Args:
            supplier_id: ID of the supplier with quality issues
            quality_data: Data about the quality issue
            
        Returns:
            bool: True if publishing was successful, False otherwise
        """
        return kafka_client.publish_event(
            self.topic,
            'quality_issue_detected',
            {
                'supplier_id': supplier_id,
                'quality_data': quality_data
            },
            key=str(supplier_id)
        )
        
    def publish_significant_rank_change(self, supplier_id: int, old_rank: int, new_rank: int, reason: str) -> bool:
        """
        Publish an event when a supplier's rank changes significantly.
        
        Args:
            supplier_id: ID of the supplier
            old_rank: Previous rank
            new_rank: New rank
            reason: Reason for the rank change
            
        Returns:
            bool: True if publishing was successful, False otherwise
        """
        return kafka_client.publish_event(
            self.topic,
            'significant_rank_change',
            {
                'supplier_id': supplier_id,
                'old_rank': old_rank,
                'new_rank': new_rank,
                'reason': reason
            },
            key=str(supplier_id)
        )


# Initialize singleton instances
supplier_consumer = SupplierEventConsumer()
ranking_producer = RankingEventProducer()
integration_producer = IntegrationEventProducer()