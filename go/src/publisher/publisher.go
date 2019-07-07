package main

import (
	"fmt"
	"gopkg.in/confluentinc/confluent-kafka-go.v1/kafka"
	"time"
	"encoding/json"
	"os"
)

func main() {

	topic := os.Getenv("publisher_topic")
	kafka_broker := os.Getenv("broker_hostname_key")
	kafka_broker_port := os.Getenv("broker_port_key")
	fmt.Printf("Topic=%s,broker=%s,port=%s\n",topic,kafka_broker,kafka_broker_port)

	p, err := kafka.NewProducer(&kafka.ConfigMap{"bootstrap.servers": kafka_broker})
	if err != nil {
		panic(err)
	}
        fmt.Printf("Created Producer %v\n", p)

	doneChan := make(chan bool)

	// Produce messages to topic (asynchronously)

	type SensorReading struct {
		Date  string
		Data string
	}

	go func() {
		defer close(doneChan)
		for e := range p.Events() {
			switch ev := e.(type) {
			case *kafka.Message:
				m := ev
				if m.TopicPartition.Error != nil {
					fmt.Printf("Delivery failed: %v\n", m.TopicPartition.Error)
				} else {
					fmt.Printf("Delivered message to topic %s [%d] at offset %v\n",
						*m.TopicPartition.Topic, m.TopicPartition.Partition, m.TopicPartition.Offset)
				}
				return

			default:
				fmt.Printf("Ignored event: %s\n", ev)
			}
		}
	}()
       for  {
	       t := time.Now().Format(time.RFC3339Nano)
		sensor := SensorReading{
			Date: t,
			Data: "ssss",
		}
		b, err := json.Marshal(sensor)
		if err != nil {
			fmt.Println("error:", err)
		}	
        	fmt.Printf("Delivering: %v\n", string(b)) 
		p.ProduceChannel() <- &kafka.Message{TopicPartition: kafka.TopicPartition{Topic: &topic, Partition: kafka.PartitionAny}, Value: []byte(b)}
	}
	// wait for delivery report goroutine to finish
	_ = <-doneChan

	p.Close()

	// Wait for message deliveries before shutting down
	p.Flush(15 * 1000)
}
