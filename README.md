# Ontorjal

Implementation of DNS client & Distance Vector Routing protocol

## DNS client

### How to run

python dns_client.py [hostname]

example hostname: facebook, facebook.com, www.facebook.com

## Distance Vector Routing protocol

### How to run
python dvr.py

### Input files
network1.txt
network2.txt

### How to change input file name in code:
- go to function: get_adjacency_matrix()
- in line number 332: change the filename (filenames are: network1.txt, network2.txt)

### How to generate output files:
python dvr.py > output.txt
