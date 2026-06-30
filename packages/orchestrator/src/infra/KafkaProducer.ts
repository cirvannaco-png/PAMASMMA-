import { IEventBus } from '@pamasmma/shared';

export class KafkaProducer implements IEventBus {
  private brokers: string[];

  constructor() {
    // Load from env: KAFKA_BROKERS=localhost:9092,localhost:9093
    const brokerList = process.env.KAFKA_BROKERS || 'localhost:9092';
    this.brokers = brokerList.split(',');
  }

  async emit(event: any): Promise<void> {
    // In production: use @confluentinc/kafka-javascript to produce to Kafka topic
    console.log(`[KafkaProducer] Emitting event to topic 'pamasmma-events':`, event);
  }

  subscribe(handler: (event: any) => void): void {
    // In production: use @confluentinc/kafka-javascript consumer group
    console.log('[KafkaProducer] Subscription registered');
  }
}
