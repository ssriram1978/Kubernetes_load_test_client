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
	message :=`{"lastUpdated": "2018-11-19T18:21:03Z","unitName": "VZW_LH_UNIT_01","unitMacId":
            "864508030027459","sensor": {"name": "cHe_AssetTracker","characteristics":
            [{"characteristicsName": "temperature","currentValue": "30.2999","readLevel":
            "R","parameterType": "Number","measurementUnit": "Celcius"}]}}`

	    p, err := kafka.NewProducer(&kafka.ConfigMap{"bootstrap.servers": kafka_broker, "acks": 0})
	if err != nil {
		panic(err)
	}
        fmt.Printf("Created Producer %v\n", p)


	// Produce messages to topic (asynchronously)

	type SensorReading struct {
		Date  string
		Data string
	}

       time.Sleep(60 * time.Second)
       for  {
	       t := time.Now().Format(time.RFC3339Nano)
		sensor := SensorReading{
			Date: t,
			Data: message,
		}
		b, err := json.Marshal(sensor)
		if err != nil {
			fmt.Printf("error:", err)
		} else {
        		fmt.Printf("Delivering: %v\n", string(b)) 
			deliveryChan := make(chan kafka.Event)
			err = p.Produce(&kafka.Message{TopicPartition: kafka.TopicPartition{Topic: &topic, Partition: kafka.PartitionAny}, Value: []byte(b)}, deliveryChan)
			e := <-deliveryChan
			m := e.(*kafka.Message)

			if m.TopicPartition.Error != nil {
				fmt.Printf("Delivery failed: %v\n", m.TopicPartition.Error)
			} else {
				fmt.Printf("Delivered message to topic %s [%d] at offset %v\n",
				*m.TopicPartition.Topic, m.TopicPartition.Partition, m.TopicPartition.Offset)
			}
		}
	}
	// wait for delivery report goroutine to finish
	p.Close()

	// Wait for message deliveries before shutting down
	p.Flush(15 * 1000)
}
