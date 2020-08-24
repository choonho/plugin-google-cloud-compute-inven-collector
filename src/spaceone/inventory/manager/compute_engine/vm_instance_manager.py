from spaceone.core.manager import BaseManager
from spaceone.inventory.model.compute import Compute
from spaceone.inventory.model.google_cloud import GoogleCloud
from spaceone.inventory.model.os import OS
from spaceone.inventory.model.hardware import Hardware


class VMInstanceManager(BaseManager):
    def __init__(self, params):
        self.params = params

    def get_server_info(self, instance, instance_types, disks, current_vo):
        '''
        server_data = {
            "name": '',
            "server_type": 'VM',
            "os_type": "LINUX" | "WINDOWS",
            "provider": "google_cloud",
            "ip_addresses": [],
            "primary_ip_address": '',
            "ip_addresses": '',
            "region_code": '',
            "region_type": ''
            "data":  {
                "os": {
                    "os_arch": "",
                    "details": "",
                    "os_distro": "",
                },
                "google_cloud": {
                    "self_link": "",
                    "fingerprint": "",
                    "reservation_affinity": "",
                    "deletion_protection": "",
                    "scheduling": {
                        'on_host_maintenance': '',
                        'automatic_restart': '',
                        'preemptible': '',
                    },
                    "labels": [{
                        key: '',
                        value: ''
                    }]
                },
                "hardware": {
                    "core": 0,
                    "memory": 0
                },
                "compute": {
                    "eip": [],
                    "keypair": "",
                    "availability_zone": "",
                    "instance_state": "",
                    "instance_type": "",
                    "launched_at": "datetime",
                    "region_name": "",
                    "instance_id": "",
                    "instance_name": "",
                    "security_groups": [],
                    "image": "",
                    "account_id": "",
                },
            }
        }
        '''

        os_type, os_data = self.get_os_type_and_data(instance)
        server_dic = self.get_server_dic(instance, os_type, current_vo)
        google_cloud_data = self.get_google_cloud_data(instance)
        hardware_data = self.get_hardware_data(instance, instance_types)
        compute_data = self.get_compute_data(instance, disks, current_vo)

        server_dic.update({
            'data': {
                'os': os_data,
                'gcp': google_cloud_data,
                'hardware': hardware_data,
                'compute': compute_data
            }
        })

        return server_dic

    def get_server_dic(self, instance, os_type, current_vo):
        server_data = {
            'name': instance.get('name', ''),
            'server_type': 'VM',
            'os_type': os_type,
            'provider': 'google_cloud',
            'primary_ip_address': self._get_primary_ip_address(instance),
            'ip_addresses': self._get_ip_addresses(instance),
            'region_code': current_vo.get('region', ''),
            'region_type': 'GOOGLE_CLOUD'
        }

        return server_data

    def get_os_type_and_data(self, instance):
        os_dists = instance.get("licenses", [])
        os_type = "LINUX"
        os_identity = ''

        for idx, val in enumerate(os_dists):
            os_items = val.split("/")
            os_identity = os_items[-1].lower()
            if idx == 0:
                if "windows" in os_identity:
                    os_type = "WINDOWS"
                break

        os_data = {
            'details': '',
            'os_distro': os_identity,
            'os_license': os_dists,
            'os_arch': ''
        }

        return os_type, OS(os_data, strict=False)

    def get_google_cloud_data(self, instance):
        google_cloud = {
            "self_link": instance.get('selfLink', ''),
            "fingerprint": instance.get('fingerprint', ''),
            "reservation_affinity": self.get_reservation_affinity(instance),
            "deletion_protection": instance.get('deletionProtection', False),
            "scheduling": self.get_scheduling(instance),
            "labels": self.get_labels(instance)
        },

        return GoogleCloud(google_cloud, strict=False)



    def get_hardware_data(self, instance, instance_types):
        '''
        core = IntType(default=0)
        memory = FloatType(default=0.0)
        is_vm = StringType(default=True)
        cpu_model = ListType(StringType(default=""))
        '''
        core, memory = self._get_core_and_memory(instance, instance_types)
        hardware_data = {
            'core': core,
            'memory': memory,
            'cpu_model': instance.get('cpuPlatform', ''),
            'is_vm': True
        }
        return Hardware(hardware_data, strict=False)

    def get_compute_data(self, instance, disks, current_vo):
        '''
            {
                'keypair': StringType(default="")
                'az':StringType()                       # zone_name
                'instance_id': StringType()
                'instance_name': StringType(default='')
                'instance_state':StringType(choices=('STAGING', 'RUNNING', 'STOPPING', 'REPAIRING'))
                'instance_type' : StringType()
                'account' : StringType()                  # Project_id
                'image' : StringType()
                'launched_at' : DateTimeType()
                tags = DictType(StringType, default={})
            }
        '''

        compute_data = {
            'keypair': '',
            'az': current_vo.get('zone', ''),            # zone_name
            'instance_id': instance.get('id'),
            'instance_name': instance.get('name', ''),
            'instance_state': instance.get('status'),
            'instance_type': self._get_instance_type(instance),
            'account': current_vo.get('project_id', ''),
            'image': self._get_image(instance, disks),
            'launched_at': instance.get('creationTimestamp'),
            'tags':  {},
        }

        return Compute(compute_data)

    @staticmethod
    def _get_images(instance, disks):
        image = ''
        name = instance.get('name')
        for disk in disks:
            if name == disk.get('name', ''):
                image = disk.get('sourceImage', '')
                break
        return image

    @staticmethod
    def _get_instance_type(instance):
        machine_type = instance.get('machineType', '')
        machine_split = machine_type.split('/')
        return machine_split[-1]

    @staticmethod
    def _get_core_and_memory(instance, instance_types):
        machine_type = instance.get('machineType', '')
        cpu = 0
        memory = 0
        for i_type in instance_types:
            if i_type.get('selfLink', '') == machine_type:
                cpu =  i_type.get('guestCpus')
                memory = round(float((i_type.get('memoryMb', 0)) / 1024), 2)
                break

        return cpu, memory


    @staticmethod
    def _get_primary_ip_address(instance):
        primary_ip_address = ''
        networks = instance.get('networkInterfaces', [])
        for i, v in enumerate(networks):
            if i == 0:
                primary_ip_address = v.get('networkIP', '')
                break
        return primary_ip_address


    @staticmethod
    def _get_ip_addresses(instance):
        ip_addresses = []
        networks = instance.get('networkInterfaces', [])
        for network in networks:
            private_ip = network.get('networkIP', '')
            access_configs = network.get('accessConfigs', [])
            if private_ip != '':
                ip_addresses.append(private_ip)

            for access_config in access_configs:
                nat_ip = access_config.get('natIP', '')
                if nat_ip != '':
                    ip_addresses.append(nat_ip)

        return ip_addresses


    @staticmethod
    def get_reservation_affinity(instance):
        ra = instance.get('reservationAffinity', {})
        return ra.get('consumeReservationType', '')

    @staticmethod
    def get_scheduling(instance):
        schedule = instance.get('scheduling', {})
        scheduling = {
            'on_host_maintenance': schedule.get('onHostMaintenance', 'MIGRATE'),
            'automatic_restart': schedule.get('automaticRestart', True),
            'preemptible': schedule.get('preemptible', False)
        }
        return scheduling

    @staticmethod
    def get_labels(instance):
        labels = []
        for k, v in instance.get('labels', {}).items():
            labels.append({
                'key': k,
                'value': v
            })
        return labels



