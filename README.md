# IOT_load_test_client
IOT_load_test_client
--------------------
Here is a Github page that details about a proposal for developing a performance load test tool for evaluating our IOT-MEC environment.

Reason:
--------
    To evaluate the latency introduced by the IOT-MEC environment and justify the value proposition that IOT on MEC provides to the enterprise users.
    To measure the performance of the IOT-MEC environment when it simultaneously handles thousands of IOT devices.
    To evaluate the various iPass solutions which are plugged into the IOT-MEC environment and that consumes, transforms and control the IOT end devices.
    To evaluate the processing delay introduced by various open source messaging queues which is the critical component of our IOT-MEC environment.
 
 Performance Parameters.
------------------------
    Latency is a time interval between the stimulation and response, or, from a more general point of view, a time delay between the cause and the effect of some physical change in the system being observed.

    From IOT perspective, Latency is the time taken between a stimulus (water leak or pressure drop from an IOT device) and a corrective response (turn off the water supply valve,send notification,...)

    Network latency in a packet-switched network is measured as either one-way (the time from the source sending a packet to the destination receiving it).

    Round-trip delay time (the one-way latency from source to destination plus the one-way latency from the destination back to the source). Round-trip latency is more often quoted, because it can be measured from a single point. Note that round trip latency excludes the amount of time that a destination system spends processing the packet.

Pros and Cons of purchasing a performance load test tool for evaluating IOT-MEC environment:
--------------------------------------------------------------------------------------------
    Pros - Perform faster evaluation of various iPass solutions and messaging queues.
    Pros - Spend more time on developing other components of IOT-MEC environment rather than developing a performance load test tool to evaluate IOT-MEC.
    Cons - Expensive. 
    Cons - Each vendor has their own proprietary tools and there is learning curve associated in getting to know how to fine tune the tool to our needs.
    
    Here are a list of MQTT performance load test vendors whom we evaluated for trial purpose. 
      Bevywise IoT Simulator
      MIMIC IOT Simulator.
      
      With both these simulators, we found that there is definitely a steep learning curve associated in using them and also they are not easily customizable to our IOT-MEC requirements.

Requirements:
-------------
    The performance load test tool shall deliver the following requirements:

    The performance load test tool shall be able to emulate/mimic thousands of IOT endpoints by authenticating and establish a secure connection with the IOT-MEC environment.
    
    The performance load test tool shall be able to provide the following options to the end user:
      For the message producer instance:
        1. An option to choose the content of the IOT message 
        
        2. An option to choose how many instances of IOT end points should it emulate.
        
        3. Frequency in seconds which translates to the the number of message to be sent in one second to the IOT-MEC environment.
        
        4. Duration in seconds of the performance load test to be conducted.
        
        5. Unique queue identifier (a topic) where the message has to be published.
        
      For the message consumer instance:
        1. Unique queue identifier (a topic) to where this consumer should subscribe to and listen for messages.
        
        2. Duration in seconds of the performance load test to be conducted.

        3. Accurately measure (in milliseconds) the end-to-end latency introduced by the IOT-MEC environment for every IOT data that it produces and that get translated to an equivalent action from the IOT-MEC environment. For this, the following steps highlight how the end-to-end latency shall be computed by the performance load test tool.

            The message producer instance shall:
                1. Insert the current date and timestamp in microseconds into the original payload which informs when the message was published to the Unique queue identifier (a topic).

            IOT-MEC environment hosting the iPass solution shall 
              1. Consume the message published to the Unique queue identifier (a topic). 
              2. Produce a corresponding action (example: turn off a water valve,...) by publishing it to another Unique queue identifier (a topic).
              3. In this process, it makes sure to copy the original sender date and timestamp from the original payload to the corresponding action payload.
              
            The message consumer instance shall:
              1. Extract the date and timestamp from the message dequeued from the Unique queue identifier (a topic) and compare it with the current date and timestamp to compute the end-to-end latency.
              
              2. After having computed the latency, the message consumer instance shall publish this information to a non volatile memory which can be further extracted, transformed and loaded into more meaningful visual graphical plots.

Evaluation of open source languages and tools for delivering the expected performance load test requirements:
-------------------------------------------------------------------------------------------------------------
      In order to scale to hundreds and thousands of producer and consumer instances, a highly resilient micro service architecture is desired.
      Producer and consumer instances shall be developed as a docker container which can be scaled to the desired limits at run time.
      The open source ELK (Elastic search, Logstash and Kibana visual boards) shall be used to depict the computed latency in visual graphical format.
      A real IOT end device shall send a maximum of 1000 message per second (one message every millisecond). 
      In order to satisfy this requirement, any high level language shall be used for development. 
      It is observed that PYTHON is the easiest and the developer friendly language that can also generate a thousand IOT messages per second.
      You really don't need a compiled in language (C,C++) for development where a simple interpreter language (shell programming, python) shall fit the requirement.
      Python provides rich options to import various plug in modules (MQTT, Kafka, ELK, Docker,....) to get the desired job done at a faster development speed.

Goals:
------
    We plan to evaluate the following options for Messaging system that could be incorporated into our MEC-IOT environment:
      RabbitMQ
      Kafka
      ZeroMQ
      NATS
      Pulsar
    We plan to evaluate the following iPass solutions that could be incorporated into our MEC-IOT environment.
      Snaplogic
      Losant
      Kafka Streams.
