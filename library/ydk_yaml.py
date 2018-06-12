from ydk.types import Empty, YType, YLeaf
from ydk.filters import YFilter

#import pydevd
#pydevd.settrace('192.168.145.1', port=55555, stdoutToServer=True, stderrToServer=True)


def compare(state, expect_key, expect_value, result=True):
    if any(isinstance(expect_value, x) for x in [str, int, bool]):
        return expect_value == state
    elif state.__class__.__name__.endswith('Enum'):
        return state.name == expect_value.iterkeys().next()
    elif not expect_value or expect_key == 'parent':
        return True
    elif isinstance(expect_value, list):
        # value is list
        # need to make sure that for each element from the expect_value list there's a match in state list
        if not isinstance(state, list):
            raise ValueError('State object is not list: {}'.format(str(state)))
        for el in expect_value:
            result = result and any(compare(new_state, expect_key, el, result) for new_state in state)
        return result
    elif isinstance(expect_value, dict):
        # value is object
        # need to make sure that all expected non-None values have a match
        if not getattr(state, '__dict__'):
            raise ValueError('State object is not class instance: {}'.format(str(state)))
        for k, v in expect_value.iteritems():
            new_state = getattr(state, k)
            result = result and compare(new_state, k, v, result)
        return result
    else:
        return ValueError('Unexpected YAML value: {} of type {}'.format(expect_value, type(expect_value)))


def instantiate_leaf(model_key, model_value):
    if isinstance(model_value, str):
        leaf_type = YType.str
    elif isinstance(model_value, int):
        leaf_type = YType.uint16
    elif isinstance(model_value, bool):
        leaf_type = YType.bool           
    leaf_instance = YLeaf(leaf_type, model_key)
    leaf_instance.set(model_value)
    return leaf_instance  


def instantiate(binding, model_key, model_value, action='assign'):
    python_special_names = [
        "class"
    ]
    if model_key in python_special_names:
        ydk_class_attribute_name = "{}_".format(model_key)
    else:
        ydk_class_attribute_name = model_key 

    if isinstance(model_value, str) and model_value.lower() == 'empty':
        if action == 'return':
            return Empty()
        elif action == 'assign':
            setattr(binding, model_key, Empty())
    elif any(isinstance(model_value, x) for x in [str, bool, int]):
#        leaf_instance = instantiate_leaf(model_key, model_value)           
        if action == 'return':
            return model_value
        elif action == 'assign':
            #setattr(binding, ydk_class_attribute_name, leaf_instance)
            setattr(binding, ydk_class_attribute_name, model_value)
    elif isinstance(model_value, list):
        list_based_instance = getattr(binding, model_key.lower())
        if type(list_based_instance).__name__ == 'YLeafList':
            for el in model_value:
#                list_based_instance.append(instantiate_leaf(model_key, el))                           
                list_based_instance.append(el)                           
        elif type(list_based_instance).__name__ == 'YList':
            for el in model_value:
                list_based_instance.append(instantiate(binding, model_key, el, action='return'))
    elif isinstance(model_value, dict):
        # special case handling enum type
        if all([x is None for x in model_value.values()]):
            enum_name = ''.join([x.capitalize() for x in model_key.split('_')])
            enum_class = getattr(binding, enum_name)
            for el in model_value.keys():
                enum = getattr(enum_class, el)
                if action == 'return':
                    return enum
                elif action == 'assign':
                    setattr(binding, ydk_class_attribute_name, enum)
        else:
            container = getattr(binding, ydk_class_attribute_name, None)
            if container and not isinstance(container, list):
                container_instance = container
            else:
                model_key_camelized = ''.join([x.capitalize() for x in model_key.split('_')])
                container_instance = getattr(binding, model_key_camelized)()
            for k, v in model_value.iteritems():
                instantiate(container_instance, k, v, action='assign')
            if action == 'return':
                return container_instance
            elif action == 'assign':
                setattr(binding, ydk_class_attribute_name, container_instance)
    elif model_value == None:
        #special case handing empty container
            model_key_camelized = ''.join([x.capitalize() for x in model_key.split('_')])
            container_instance = getattr(binding, model_key_camelized)()
            if action == 'return':
                return container_instance
            elif action == 'assign':
                setattr(binding, ydk_class_attribute_name, container_instance)       
    else:
        raise ValueError('Unexpected YAML value: {} of type {}'.format(model_value, type(model_value)))


class YdkModel:
#    def __init__(self, model, data):
#        self.model = model
#        self.data = data
#        self.binding = None
    def __init__(self, config):
        self.config = config ##list
        self.bindings = list()      
        self.root_yang_model_names = list()

    def build_ydk_object_hierarchy(self):
        for root_yang_model_name, root_yang_model_data in self.config.iteritems():
            if root_yang_model_name == 'interfaces':
                from ydk.models.ietf_ip_interface import ietf_interfaces
                current_binding = ietf_interfaces.Interfaces()
            elif any(root_yang_model_name == x for x in ['native']):
                from ydk.models.cisco_ios_xe.ned import Native
                current_binding = Native()
            elif root_yang_model_name == 'configuration':
                from ydk.models.junos.configuration import Configuration
                current_binding = Configuration()
            elif root_yang_model_name == 'openconfig-bgp':
                from ydk.models.openconfig_bgp_policy import openconfig_bgp
                current_binding = openconfig_bgp.Bgp()
            elif root_yang_model_name == 'openconfig-policy':
                from ydk.models.openconfig_bgp_policy import openconfig_routing_policy
                current_binding = openconfig_routing_policy.RoutingPolicy()
            elif root_yang_model_name == 'openconfig-interfaces':
                from ydk.models.openconfig_bgp_policy import openconfig_interfaces
                current_binding = openconfig_interfaces.Interfaces()
            else:
                raise ValueError('Untested or not implemented configuration model {}'.format(root_yang_model_name))
            for k, v in root_yang_model_data.iteritems():
                instantiate(current_binding, k, v)
            self.bindings.append(current_binding)
            self.root_yang_model_names.append(root_yang_model_name)

#        if self.model == 'interfaces':
#            from ydk.models.ietf_ip_interface import ietf_interfaces
#            self.binding = ietf_interfaces.Interfaces()
#        elif any(self.model == x for x in ['native']):
#            from ydk.models.cisco_ios_xe.ned import Native
#            self.binding = Native()
#        elif self.model == 'configuration':
#            from ydk.models.junos.configuration import Configuration
#            self.binding = Configuration()
#        elif self.model == 'openconfig-bgp':
#            from ydk.models.openconfig_bgp_policy import openconfig_bgp
#            self.binding = openconfig_bgp.Bgp()
#        elif self.model == 'openconfig-policy':
#            from ydk.models.openconfig_bgp_policy import openconfig_routing_policy
#            self.binding = openconfig_routing_policy.RoutingPolicy()
#        elif self.model == 'openconfig-interfaces':
#            from ydk.models.openconfig_bgp_policy import openconfig_interfaces
#            self.binding = openconfig_interfaces.Interfaces()
#        else:
#            raise ValueError('Untested or not implemented configuration model {}'.format(self.model))
#        for k, v in self.data.iteritems():
#            instantiate(self.binding, k, v)


#    def configure(self, device):
#        self.action('create', device)
#        return True

    def connect_and_provision(self, device):
        from ydk.providers import NetconfServiceProvider
        from ydk.services import NetconfService, Datastore
        provider = NetconfServiceProvider(address=device['hostname'],
                                          port=device['port'],
                                          username=device['username'],
                                          password=device['password'],
                                          protocol='ssh')
        netconf = NetconfService()
        if "configuration" in self.root_yang_model_names:
            netconf.lock(provider, Datastore.candidate)
            result = netconf.edit_config(provider, Datastore.candidate, self.bindings)
            netconf.commit(provider)
            netconf.unlock(provider, Datastore.candidate)
        return result


    def merge(self, device):
        self.connect_and_provision(device)
        return True


#    def sync_to(self, device):
#        if "configuration" in self.root_yang_model_names:
#            for binding in self.bindings:
#                binding.yfilter = YFilter.replace
#        self.connect_and_provision(device)
#        return True


    def sync_to(self, device):
        if "configuration" in self.root_yang_model_names:
#            self.set_replace_tags_for_vsrx()
            self.set_replace_tags()
        self.connect_and_provision(device)
        return True


    def set_replace_tags(self):
        for binding in self.bindings:    
            binding.yfilter = YFilter.replace



    def set_replace_tags_for_vsrx(self):
        for binding in self.bindings:
            ydk_class_attribute_name_list = [
                child_class_tuple[0] for child_class_tuple in binding._child_classes.itervalues()
            ]
            for ydk_class_attribute_name in ydk_class_attribute_name_list:
                if ydk_class_attribute_name not in [
                    "access_profiles",
                    "vmhost",
                    "jnx_example",
                    "virtual_chassis",
                    "dynamic_profiles",
                    "multi_chassis",
                    "bridge_domains",
                    "event_options"
                ]:  
                    ydk_class_attribute_value = getattr(binding, ydk_class_attribute_name)
                    if ydk_class_attribute_value == None:
                        ydk_class_name = ''.join([x.capitalize() for x in ydk_class_attribute_name.split('_')])
                        ydk_class_attribute_value = getattr(binding, ydk_class_name)()
                    ydk_class_attribute_value.yfilter = YFilter.replace






def apply_wa(binding, some_dict, non_root_level=False):
    ydk_class_attribute_name_list = [
        child_class_tuple[0] for child_class_tuple in binding._child_classes.itervalues()
    ] 
    unreplaceble_attribute_names = [x for x in some_dict.iterkeys()]
    with open("/root/wa.log", "w") as logfile:       
        for ydk_class_attribute_name in ydk_class_attribute_name_list:    
            if ydk_class_attribute_name not in unreplaceble_attribute_names:
                if not non_root_level:
                    pass
                else :
                    if getattr(binding, ydk_class_attribute_name) is  None:
                        ydk_class_name = ''.join([x.capitalize() for x in ydk_class_attribute_name.split('_')])
                        current_instance = getattr(binding, ydk_class_name)()
                        setattr(binding, ydk_class_attribute_name, current_instance)
                    else:                    
                        current_instance = getattr(binding, ydk_class_attribute_name)
                    current_instance.yfilter = YFilter.replace
            else:
                if isinstance(some_dict[ydk_class_attribute_name], dict):
                    current_instance = getattr(binding, ydk_class_attribute_name)
                    current_instance.yfilter = YFilter.not_set
                    apply_wa(current_instance, some_dict[ydk_class_attribute_name], non_root_level=True)
                else:
                    ydk_class_name = ''.join([x.capitalize() for x in ydk_class_attribute_name.split('_')])
                    current_instance = getattr(binding, ydk_class_name)() 
                    setattr(binding, ydk_class_attribute_name, current_instance)
            logfile.writelines(
                [
                    str(ydk_class_attribute_name_list),
                    "\n-----------------------------------\n",
                    str(unreplaceble_attribute_names),
                    "\n-----------------------------------\n",
                    str(ydk_class_attribute_name),
                    "\n************************************\n"
                ]
            )



