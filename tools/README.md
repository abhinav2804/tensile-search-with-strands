# The GIES (Generalised Indexer for ElasticSearch)

## Project Description
Our project is based on a great idea which helps us index any data provided in a file to our elasticIndex. Our process generates runs the flow in the following way:
1. send the csv, that has your data is represented in and generates an index over the elastic.
2. We can send the query in Natural language and LLM+MCP will together bring the dream of fetching data easily.

## Impact of the Project
1. If I am able to index anthing I need, using the best indexing setting and mapping which are based on data and queries that owner gives. 
2. This is first of its kind as even elasticsearch doesnt work on analyzer, but we are working on the same.
3. This will take away the load of being an expert in elastic before indexing the same and shall help in making the system more robust for searching. 

## Team

- **Team Name:** IM GPT  
- **Members:**
  - Paras Lehana  
  - Abhinav Kaushik  
  - Khem Chand  
  - Amit Kumar  



## Hackathon Theme / Challenge
- **Theme:** Theme 2
- **Challenge:**
Example user query:  
> “Want to buy red or orange LED from Syska or better brands, under 10 wattage.”

We understand:
- The query refers to an **LED Bulb**, not a TV.  
- **9-watt** will work, but **blue color** should be excluded.  
- **Syska** is preferred.  

This type of intelligent contextual understanding is **not possible with leading e-commerce platforms** at the moment.  
That’s why we are **hacking the impossible**!

- **Cherry On The Cake**

We understand:
- Data provided by the user in **csv format**.
- **Few queries** that user thinks their **clients will search**

We **generate a well suited index** for the given situation that helps **producing beautiful response within few seconds from elastic**.



## What We Built & How to Run It

### Steps to Run
1. **Run N8N Workflow tool** using Docker Compose:  
   ```bash
   docker-compose -f N8N/docker-compose.yml up -d

2. Run Elasticsearch & Kibana from official DockerHub images.
3. Run Elastic MCP Server using: 
   docker-compose -f ElasticMPCServer/docker-compose.yml up -d
4. Import N8N workflow:

  Import the file: N8N/My workflow.json into N8N.

    The workflow uses an AI Agent with:

    1 Tools and 1 Model via OpenAI Chat Model
    a) Claude API model (set your API key)
    b) Elastic MCP Server – **hosted on Cequence**, interacts with the LLM to reason and fetch data from Elasticsearch (set encoded authorization key for Elasticsearch DB authentication)


### Tech Stack

  Elasticsearch
  Kibana
  ElasticSearch MCP Server
  LLM Model – Claude
  N8N Workflow Orchestration
  Descope
  Cequence
  Java



### Demo Video

   👉 Link coming soon...
