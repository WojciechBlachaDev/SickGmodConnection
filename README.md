# SickGmodConnection
Communication script to receive and send data to SICK. FlexiCPU via GMOD gateway.
Sending is setted to write all avaible data points so please enable all datasets in the gateway configuration.
Reading is setted to read only Data set 1 ( 50 configurable bytes ).

The communication is in the two topics:

1.Gmod/Write_data - this topic allows you to write data to GMOD. To use it you must from sick_gmod_communication.msg import gmod_in.
2.Gmod/Data_readed - this topic shares readed data from GMOD. For using it you must from sick_gmod_communication.msg import gmod_out.

All the Data sets and bits are the same as in the gateway.

**REQUIREMENTS**
1. pyModbusTCP (https://pypi.org/project/pyModbusTCP/#description)
2. rospy (http://wiki.ros.org/rospy)
3. rospkg (http://wiki.ros.org/rospkg)
4. yaml (pip install PyYAML)
5. ROS custom_msgs

**User settings**
User can edit 4 main settings: 
1. IpAddress - the address of your device ( default: 192.168.1.11 )
2. Port - the port for communication ( default: 502 )
3. Refresh rate - speed of communication refreshing ( default 20 Hz )
4. Timeout - timeout for trying to connect to device ( default 2 seconds )

Settings are available in the config folder in config.yaml file. Please use it carefully.

**GATEWAY DEFAULT CONFIG IN SAFETY DESIGNER**
![Zrzut ekranu 2024-01-11 102214](https://github.com/WojciechBlachaDev/SickGmodConnection/assets/156101476/18e296b5-bb47-401d-96fc-b89f6c55a778)
![Zrzut ekranu 2024-01-11 102231](https://github.com/WojciechBlachaDev/SickGmodConnection/assets/156101476/e065632a-8f9c-4ac2-8d7e-ac08990b5f51)
