# Guide to use this folder on Jetson Nano Developer kit B01

## Prerequisites 
- NVIDIA Jetson Nano Dev Kit B01 
- AT8236 motor control (It should be the same PINOUT as TB6612)
- ESP32S3 dev board 

## System 
- Jetpack 4.6.1 


## What I exactly do after the fisrt system boot
```
sudo apt update
```
This fetches the packages to update 

```
sudo apt upgrade
```
This upgrades all the packages 

!!!Don't do it tho!!!

This may cause some trouble with existing nvidia preconfiged file like l4t

```
python3 --version 
```
This checks if python3 installed and the version is 3.6.9

```
sudo apt-get install python3-flask
```
This installs flask, our webpage server

opencv should be preinstalled with jetpack 4.6.1

jetson-gpio is also installed 

This should do the job before we run the program,