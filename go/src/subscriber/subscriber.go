package main

import (
	"fmt"
	"gopkg.in/confluentinc/confluent-kafka-go.v1/kafka"
	"encoding/json"
	"time"
	"os"
)

func main() {
        topic := os.Getenv("subscriber_topic")
        kafka_broker := os.Getenv("broker_hostname_key")
        kafka_broker_port := os.Getenv("broker_port_key")
        fmt.Printf("Topic=%s,broker=%s,port=%s\n",topic,kafka_broker,kafka_broker_port)

	c, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": kafka_broker,
		"group.id":          "subscriber-golang-group",
		"auto.offset.reset": "latest",
	})

	if err != nil {
		panic(err)
	}

        type SensorReading struct {
                Date  string
                Data string
        }

	c.SubscribeTopics([]string{topic, "^aRegex."}, nil)

	for {
		msg, err := c.ReadMessage(-1)
		if err == nil {
		        var sensor_reading SensorReading
			//fmt.Printf("Message on %s: %s\n", msg.TopicPartition, string(msg.Value))
			err := json.Unmarshal(msg.Value, &sensor_reading)
			if err != nil {
				fmt.Printf("error:", err)
			}
			//fmt.Printf("sensor_reading=%+v", sensor_reading)
			t1, err := time.Parse(
        			time.RFC3339Nano,
        			sensor_reading.Date)
			if err == nil  {
				elapsed := time.Since(t1)
				fmt.Printf("Latency=%s\n",elapsed)
			}
		} else {
			// The client will automatically try to recover from all errors.
			fmt.Printf("Consumer error: %v (%v)\n", err, msg)
		}
	}

	c.Close()
}
