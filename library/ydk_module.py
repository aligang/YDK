from ansible.module_utils.basic import AnsibleModule
from ydk_yaml import YdkModel
import logging

def main():
    arguments = dict(
        hostname=dict(type='str'),
#        model=dict(type='str'),
#        data=dict(type='dict'),
        config=dict(type='dict'),
        action=dict(type='str'),
        username=dict(type='str'),
        password=dict(type='str')
    )
    module = AnsibleModule(
        argument_spec = arguments,
        supports_check_mode=True
        )


    log_ydk = logging.getLogger('ydk')
    log_ydk.setLevel(logging.DEBUG)
    handler = logging.FileHandler("/root/ydk.log")
    log_ydk.addHandler(handler)

    
    ydk_model = YdkModel( module.params['config'])
    ydk_model.build_ydk_object_hierarchy()

    ydk_action = getattr(ydk_model, module.params['action'])

    device = {'hostname': module.params['hostname'], 'port': 830,
              'username':  module.params['username'],
              'password':  module.params['password']}

    rc = ydk_action(device)
    if rc == True and module.params['action'] == 'merge':
        module.exit_json(changed=True)
    if rc == True and module.params['action'] == 'sync_to':
        module.exit_json(changed=True)
#    elif rc and module.params['action'] == 'verify':
#        module.exit_json(changed=False)
    else:
        module.fail_json(msg="YDK module has failed with action {}".format(module.params['action']))

if __name__ == '__main__':
    main()
