#!/usr/bin/env python3
import rospy, rospkg, yaml, time, ipaddress
from pyModbusTCP.client import ModbusClient
from bitstring import BitArray
from sick_gmod_communication.msg import gmod_in as Gmod_in, gmod_out as Gmod_out

class ReadSettings:
    def __init__(self, communication_instance):
        super(ReadSettings, self).__init__()
        self.communication = communication_instance
        self.config = None
        self.tmp_ip_address = ''
        self.tmp_port = 0
        self.tmp_refresh_rate = 0
        self.tmp_connection_timeout = 0.0
        self.SetOptions()
        

    def SetOptions(self):
        try:
            self.config = self.ReadYamlConfigFile()
        except Exception as e:
            rospy.logfatal(f'Set options exception: {e}')
        rospy.loginfo(self.config)
        self.tmp_ip_address = self.config['ip_address']
        self.tmp_port = self.config['port']
        self.tmp_connection_timeout = self.config['connection_timeout']
        self.tmp_refresh_rate = self.config['refresh_rate']
        self.communication.user_config_verification = self.VerifyConfigData()
        self.communication.ip_address = self.tmp_ip_address
        self.communication.port = self.tmp_port
        self.communication.connection_timeout = self.tmp_connection_timeout
        self.communication.refresh_rate = self.tmp_refresh_rate

    def ReadYamlConfigFile(self):
        rospack = rospkg.RosPack()
        package_path = rospack.get_path('sick_gmod_communication')
        yaml_file_path = package_path + '/config/config.yaml'
        with open(yaml_file_path, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def VerifyConfigData(self):
        tmp = self.VerifyIpAddress()
        if not tmp:
            rospy.logfatal(f'Verification of config file - wrong ip address: {self.tmp_ip_address}')
        tmp = self.VerifyPort()
        if not tmp:
            rospy.logfatal(f'Verification of config file - wrong port: {self.tmp_port}')
        else:
            if self.tmp_port != 502:
                rospy.logwarn(f'Used port: {self.tmp_port}. This is not default MODBUS port for communication. Please chceck again if you have any problem with communication')
        tmp = self.VerifyConnectionTimeout()
        if not tmp:
            rospy.logfatal(f'Verification of config file - wrong connection timeout value: {self.tmp_connection_timeout}')
        tmp = self.VerifyRefreshRate()
        if not tmp:
            rospy.logfatal(f'Verification of config file - wrong refresh rate: {self.tmp_refresh_rate}')
        return tmp
    def VerifyConnectionTimeout(self):
        try:
            timeout_value = float(self.tmp_connection_timeout)
            return timeout_value > 0
        except ValueError:
            return False
    
    def VerifyRefreshRate(self):
        try:
            refresh_rate = int(self.tmp_refresh_rate)
            return refresh_rate > 0
        except ValueError:
            return False

    def VerifyIpAddress(self):
        try:
            ip = ipaddress.ip_address(self.tmp_ip_address)
            return True
        except ValueError:
            return False
    
    def VerifyPort(self):
        try:
            port_num = int(self.tmp_port)
            return 1 <= port_num <= 65535
        except ValueError:
            return False


class CommunicationSequence:
    def __init__(self):
        self.ip_address = ''
        self.port = 0
        self.connection_timeout = 0.0
        self.refresh_rate = 0
        self.default_rate = 10
        self.user_config_verification = False
        self.read_settings = ReadSettings(self)  # Przekazanie instancji samej siebie do ReadSettings
        self.connection_status = False
        self.data_to_write = Gmod_in()
        self.readed_data = Gmod_out()
        self.gmod_gateway = ModbusClient()
        self.sleep = rospy.Rate(self.refresh_rate)

        if self.user_config_verification:
            while not rospy.is_shutdown():
                try:
                    data_to_write_sub = rospy.Subscriber('Gmod/Write_data', Gmod_in, self.DataToWriteCallback)
                    self.received_data_pub = rospy.Publisher('Gmod/Data_readed', Gmod_out, queue_size=1)
                except Exception as e:
                    rospy.logerr(f'Main loop exception: {e}')
                if not self.connection_status:
                    self.Connect()
                if self.connection_status:
                    self.WriteDataToGmod()
                    self.ReadDataFromGmod()
                    self.PublishReadedData()
                self.sleep.sleep()

    def Colorize(self, text, color_code):
        return "\033[{}m{}\033[0m".format(color_code, text)
    def PrintGreen(self, message):
        print(self.Colorize(message, '92'))
    
    def DataToWriteCallback(self, msg):
        self.data_to_write = msg
    
    def Connect(self):
        try: 
            if self.gmod_gateway.is_open():
                self.gmod_gateway.close()
            self.gmod_gateway = ModbusClient(self.ip_address, self.port, timeout=self.connection_timeout, auto_open=True, auto_close=True)
            start_time = time.time()
            timeout = 10
            while ((time.time() - start_time) < timeout):
                self.gmod_gateway.open()
                self.connection_status = self.gmod_gateway.is_open()
                self.gmod_gateway.close()
                if ((time.time() - start_time) > timeout):
                    self.connection_status = False
                    rospy.logerr('====================================')
                    rospy.logerr('           FLEXICPU NOT CONNECTED')
                    rospy.logerr('====================================')
                    break
                if self.connection_status:
                    self.PrintGreen('====================================')
                    self.PrintGreen('           FLEXICPU CONNECTED')
                    self.PrintGreen('====================================')
                    break
        except (ValueError) as e:
            rospy.logerr(f'ConnectionFlexiCPU: Connect error: {e}')

    def WriteConversion(self, bits):
        try:
            for bit in bits:
                result = (result << 1) | bit
            return result
        except Exception as e:
            rospy.logwarn(f'Exception occured during bit array conversion: {e}')
            return None
    
    def ReadConversion(self, data):
        try:
            filtered_data = list()
            for item in data:
                item_repr = bin(item)[2:].zfill(16)
                reversed_item = item_repr[::-1]
                filtered_data.append(reversed_item)
            separated_data = [bit for binary_str in filtered_data for bit in binary_str]
            bool_list = [bool(int(bit)) for binary_str in separated_data for bit in binary_str]
            return bool_list
        except Exception as e:
            rospy.logerr(f'Exception occured when converting readed data...')

    def WriteDataToGmod(self):
        bits = BitArray(400)
        bits_divided = [BitArray(16) for _ in range(25)]
        try:
            for i in range(50):
                current_bitset = getattr(self.data_to_write, f'BitSet{i}')
                for j in range(8):
                    current_bit_value = getattr(current_bitset, f'Bit{j}')
                    index = i * 8 + j
                    bits[index] = current_bit_value if current_bit_value is not None else False
        except Exception as e:
            rospy.logwarn(f'Exception occurred when trying to get attributes: {e}')
        try:
            for i in range(25):
                start_bit = i * 16
                end_bit = start_bit + 16
                bits_divided[i] = bits[start_bit:end_bit][::-1] if bits[start_bit:end_bit] is not None else BitArray(16)
        except Exception as e:
            rospy.logwarn(f'Exception occurred when trying to split bits to words: {e}')
        if bits_divided is not None:
            try:
                bits_divided_as_int = [int(word.uint) for word in bits_divided]
                write_check = self.gmod_gateway.write_multiple_registers(1999, bits_divided_as_int)
                if not write_check:
                    self.connection_status = False
                    rospy.logerr(f'Problem with connection occured while sending data: {e}. Reconnecting...')
            except Exception as e:
                rospy.logerr(f'Exception occurred when trying to send GMOD data: {e}')

    def ReadDataFromGmod(self):
        readed_data = self.gmod_gateway.read_holding_registers(1099, 25)
        if readed_data == None:
            self.connection_status = False
            rospy.logerr(f'Problem with connection occured while reading data: {e}. Reconnecting...')
        result = self.ReadConversion(readed_data)
        if len(result) > 0:
            try:
                for i in range(len(result)):
                    bit_set_index = i // 8
                    bit_index = i % 8
                    setattr(getattr(self.readed_data, f'BitSet{bit_set_index}'), f'Bit{bit_index}', result[i])
            except Exception as e:
                rospy.logfatal(f'Exception occured when assigning readed data to variables: {e}')

    def PublishReadedData(self):
        self.received_data_pub.publish(self.readed_data)

if __name__ == '__main__':
    try:
        rospy.loginfo('Starting GMOD communication script...')
        rospy.init_node('gmod_node')
        communication = CommunicationSequence()
        rospy.spin()
    except (Exception, BaseException) as e:
        rospy.logfatal(f'Starting GMOD failed: {e}')
