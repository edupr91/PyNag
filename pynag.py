#!/usr/bin/python
"""
Script inspired in the nagios_commander
"""
import re
import requests
import argparse
import json
import webbrowser
from datetime import datetime
from termcolor import cprint


from PyInquirer import prompt, Separator


parser = argparse.ArgumentParser(
    description='Nagios Python CLI'
)

parser.add_argument('--host', '-H',
                    help='list all hosts status, Send "all" to list all host status',
                    )
parser.add_argument('--service_status', '-S',
                    help='Service Status Details a specific host. '
                         'Send "all" to see all hosts problems services status',
                    action='store_true'
                    )


args = vars(parser.parse_args())


ACK_MESSAGE = 'Not critical or being worked on'
NAGIOS_INSTANCE = 'https://<nagios.domain.com>/nagios/cgi-bin'
http_user = '<my_user>'
http_password = '<super_secret_password>'

test_request = requests.get(NAGIOS_INSTANCE, auth=(http_user, http_password))
if test_request.status_code != 200:
    print("Wrong credentials")
    exit(1)


def do_post_request(url, user, password, params=None):
    req = requests.get(url, auth=(user, password), params=params)
    if test_request.status_code != 200:
        print("Smth went wrong")
    else:
        return req.text


def get_all_hosts_status():
    # Get hosts list
    # https://nagios.domain.com/nagios/cgi-bin/status.cgi?hostgroup=all&style=hostdetail
    data = {
        'hostgroup': 'all',
        'style': 'hostdetail',
        'start': '0',
        'limit': '500'  # Set limit 500 hosts.
    }

    html_output = do_post_request(http_user, http_password, data)
    # https://nagios.domain.com/nagios/cgi-bin/status.cgi?hostgroup=all&style=hostdetail
    html_hosts = str.splitlines(html_output)

    hosts_re = re.compile("<td align=left valign=center class='statusHOSTUP'>")
    hosts_raw = list(filter(hosts_re.match, html_hosts))
    host_output_hash = []
    for host_line_raw in hosts_raw:
        host_clean = re.sub('^<td.*title=.*\'>', '', host_line_raw)
        host_clean = re.sub('</.*$', '', host_clean)
        host_index = html_hosts.index(host_line_raw)
        host_status_index = host_index + 15
        host_status_raw = html_hosts[host_status_index]
        host_status_clean = re.sub('^<td.*\'>', '', host_status_raw)
        host_status_clean = re.sub('</td>$', '', host_status_clean)
        host_output_hash += [host_clean + "\t\t" + host_status_clean]

    print("\n".join(host_output_hash))


def nagios_request_validation(req_output, host, service, task):
    ok_string = re.search(
        '.*Your command request was successfully submitted to Nagios for processing.*',
        req_output
    )
    if ok_string:
        cprint(
            '{host} - {task} - {service}: Your command request was successfully submitted to Nagios for'
            ' processing'.format(
                host=host,
                service=service,
                task=task
            ),
            'green'
        )
    else:
        cprint(
            '{host} - {task} - {service}: Your command request WAS NOT successfully submitted'.format(
                host=host,
                service=service,
                task=task
            ),
            'red',
            attrs=['bold']
        )


def get_all_service_status():
    # https://nagios.domain.com/nagios/cgi-bin/status.cgi?host=all&servicestatustypes=28
    data = {
        'host': 'all',
        'servicestatustypes': '28',
    }
    nagios_url = NAGIOS_INSTANCE + '/status.cgi'
    all_service_status_request = do_post_request(nagios_url, http_user, http_password, data)
    html_hosts = str.splitlines(all_service_status_request)
    # <td align=left valign=center class='*'>
    hosts_re = re.compile("<td align=left valign=center class='.*'>")
    hosts_raw = list(filter(hosts_re.match, html_hosts))
    service_hash = {}
    menu = []
    for host_line_raw in hosts_raw:
        host_clean = re.sub('^<td.*title=.*\'>', '', host_line_raw)
        host_clean = re.sub('</.*$', '', host_clean)
        host_index = html_hosts.index(host_line_raw)
        current_host_html = []
        index = host_index
        while True:
            index = index + 1
            # safe way to check if we have arrived at the end of the index
            try:
                next_line = html_hosts[index]
            except IndexError:
                break
            # check if we got another host line
            foo = hosts_re.match(next_line)
            if foo:
                break
            else:
                # print('get info from {}'.format(host_clean))
                current_host_html = current_host_html + [next_line]
# <td align='left' valign=center class='statusBGWARNING'><a href='extinfo.cgi?type=2&host=web01.foo.net&service
        service_re = re.compile(
            "<td align='left' valign=center class='.*'><a href=.*&service"
        )
        services_raw = list(filter(service_re.match, current_host_html))
        service_host_hash = {}
        host_menu_string = '{host} (& sub services)'.format(host=host_clean)
        menu = menu + [{'name': host_menu_string}]

        for service_line_raw in services_raw:
            service_clean = re.sub("^<td align='left' valign=center class='.*'><a.*'>", '', service_line_raw)
            service_clean = re.sub('</.*$', '', service_clean)

            # get service details
            service_index = html_hosts.index(service_line_raw)
            s_status_html = html_hosts[service_index + 11]
            s_status = re.sub("^<td.*'>", '', s_status_html)
            s_status = re.sub('</.*$', '', s_status)

            s_last_check_html = html_hosts[service_index + 12]
            s_last_check = re.sub("^<td.*nowrap>", '', s_last_check_html)
            s_last_check = re.sub('</.*$', '', s_last_check)

            s_duration_html = html_hosts[service_index + 13]
            s_duration = re.sub("^<td.*nowrap>", '', s_duration_html)
            s_duration = re.sub('</.*$', '', s_duration)

            s_attempts_html = html_hosts[service_index + 14]
            s_attempts = re.sub("^<td.*'>", '', s_attempts_html)
            s_attempts = re.sub('</.*$', '', s_attempts)

            s_info_html = html_hosts[service_index + 15]
            s_info = re.sub("^<td.*'>", '', s_info_html)
            s_info = re.sub('</.*$', '', s_info)
            s_info = re.sub('&nbsp;', '', s_info)
            s_info = re.sub('&quot;', '', s_info)

            # find out acknowledge
            s_ack = False
            s_mute = False
            details_line = html_hosts[service_index + 6]
            ack_match = re.search('.*This service problem has been acknowledged.*', details_line)
            if ack_match:
                s_ack = True
                ack_string = '✔ ️'
            else:
                s_ack = False
                ack_string = '  ️'

            # find out disabled notif
            mute_match = re.search('.*Notifications for this service have been disabled.*', details_line)
            if mute_match:
                s_mute = True
                mute_string = '🔇'
            else:
                s_mute = False
                mute_string = '  '

            entry_suffix = ack_string + mute_string

            service_host_hash[service_clean] = {
                'status': s_status,
                'last_check': s_last_check,
                'duration': s_duration,
                'attempts': s_attempts,
                'info': s_info,
                'ack': s_ack,
                'notifications': s_mute,
            }
            new_menu_content = '{suffix} - {host} - {status} - {service} - {attempts} - {info}'.format(
                suffix=entry_suffix,
                host=host_clean,
                service=service_clean,
                status=s_status,
                attempts=s_attempts,
                info=s_info
            )
            menu = menu + [{'name': new_menu_content}]
        service_hash[host_clean] = service_host_hash

    questions = [
        {
            'type': 'checkbox',
            'qmark': '😃',
            'message': 'Service Status Details For All Hosts',
            'name': 'service_status',
            'choices': menu,
            'validate': lambda answer: 'You must choose at least one topping.'
            if len(answer) == 0 else True
        }
    ]
    answers = prompt(questions)
    return answers, service_hash


def do_actions(actions_service_status, services_hash):
    selected_answers = {}
    for service_status in actions_service_status['service_status']:
        host_match = re.search('.*sub services.*', service_status)
        if host_match:
            host = service_status.split(' ')[0]
            service = 'all'
        else:
            host = service_status.split(' - ')[1]
            service = service_status.split(' - ')[3]

        if host in selected_answers:
            selected_answers[host] = selected_answers[host] + [service]
        else:
            selected_answers[host] = [service]

    if len(selected_answers) == 0:
        print("You haven't selected any option, use <space> to mark the service you want to work with...")
        exit()

    print(json.dumps(selected_answers, indent=2, sort_keys=True))
    # Add option
    # recheck
    # ack - remove ack
    # disable notif - Enable notif
    # open in browser
    print("you have selected the following services")
    question = [
        {
            'type': 'confirm',
            'message': 'Do you want to continue?',
            'name': 'continue',
            'default': True,
        }
    ]
    confirm = prompt(question)
    if confirm['continue']:
        action_question = [
            {
                'type': 'list',
                'name': 'action',
                'message': 'What do you want to do?',
                'choices': [
                    'Open in browser',
                    'Recheck',
                    'ACK - Remove ACK',
                    'Disable Notif',
                    'Enable Notif',
                    'Exit'
                ],
                # 'filter': lambda val: val.lower()
            },
        ]
        action_selected = prompt(action_question)
        if action_selected['action'] == 'Open in browser':
            # NAGIOS_INSTANCE = 'https://nagios.evilcorp.com/nagios/cgi-bin'
            # /extinfo.cgi?type=2&host=foo.bar.org&service=disk
            for host in selected_answers:
                for service in selected_answers[host]:
                    if service == 'all':
                        url = NAGIOS_INSTANCE + "/status.cgi?host={host}".format(
                            host=host,
                            service=service,
                        )
                    else:
                        url = NAGIOS_INSTANCE + "/extinfo.cgi?type=2&host={host}&service={service}".format(
                            host=host,
                            service=service,
                        )
                    webbrowser.open(url)
        elif action_selected['action'] == 'Recheck':
            now = datetime.now()
            date_time = now.strftime("%y-%-m-%d %H:%M:%S")
            for host in selected_answers:
                for service in selected_answers[host]:
                    if service == 'all':
                        cmd_typ = '17'  # CMD_SCHEDULE_HOST_SVC_CHECKS
                    else:
                        cmd_typ = '7'  # CMD_SCHEDULE_SVC_CHECK
                    data = {
                        'host': host,
                        'cmd_typ': cmd_typ,
                        'cmd_mod': '2',
                        'btnSubmit': 'Commit',
                        'service': service,
                        'start_time': date_time,
                        'force_recheck': 'on',
                    }
                    nagios_url = NAGIOS_INSTANCE + '/cmd.cgi'
                    req_output = do_post_request(nagios_url, http_user, http_password, data)
                    nagios_request_validation(req_output, host, service, 'recheck')
        elif action_selected['action'] == 'ACK - Remove ACK':
            # FIXME ACK doesn't work when service = all
            for host in selected_answers:
                for service in selected_answers[host]:
                    # host_ack = services_hash[host]
                    if services_hash[host][service]['ack']:
                        if service == 'all':
                            cmd_type = '51'  # CMD_REMOVE_HOST_ACKNOWLEDGEMENT
                        else:
                            cmd_type = '52'  # CMD_REMOVE_SVC_ACKNOWLEDGEMENT
                        data = {
                            'host': host,
                            'cmd_typ': cmd_type,
                            'cmd_mod': '2',
                            'btnSubmit': 'Commit',
                            'service': service,
                        }
                        nagios_url = NAGIOS_INSTANCE + '/cmd.cgi'
                        req_output = do_post_request(nagios_url, http_user, http_password, data)
                        nagios_request_validation(req_output, host, service, 'remove_ack')
                    else:
                        # no ack
                        if service == 'all':
                            cmd_type = '33'  # CMD_ACKNOWLEDGE_HOST_PROBLEM
                        else:
                            cmd_type = '34'  # CMD_ACKNOWLEDGE_SVC_PROBLEM
                        data = {
                            'host': host,
                            'cmd_typ': cmd_type,
                            'cmd_mod': '2',
                            'btnSubmit': 'Commit',
                            'service': service,
                            'sticky_ack': 'on',
                            'send_notification': 'on',
                            'com_data': ACK_MESSAGE,
                        }
                        nagios_url = NAGIOS_INSTANCE + '/cmd.cgi'
                        req_output = do_post_request(nagios_url, http_user, http_password, data)
                        nagios_request_validation(req_output, host, service, 'send_ack')
        elif action_selected['action'] == 'Disable Notif':
            for host in selected_answers:
                for service in selected_answers[host]:
                    if service == 'all':
                        cmd_type = '29'  # CMD_DISABLE_HOST_SVC_NOTIFICATIONS
                    else:
                        cmd_type = '23'  # CMD_DISABLE_SVC_NOTIFICATIONS
                    data = {
                        'host': host,
                        'cmd_typ': cmd_type,
                        'cmd_mod': '2',
                        'btnSubmit': 'Commit',
                        'service': service,
                    }
                    nagios_url = NAGIOS_INSTANCE + '/cmd.cgi'
                    req_output = do_post_request(nagios_url, http_user, http_password, data)
                    nagios_request_validation(req_output, host, service, 'disable_notif')
        elif action_selected['action'] == 'Enable Notif':
            for host in selected_answers:
                for service in selected_answers[host]:
                    if service == 'all':
                        cmd_type = '28'  # CMD_ENABLE_HOST_SVC_NOTIFICATIONS
                    else:
                        cmd_type = '22'  # CMD_ENABLE_SVC_NOTIFICATIONS

                    data = {
                        'host': host,
                        'cmd_typ': cmd_type,
                        'cmd_mod': '2',
                        'btnSubmit': 'Commit',
                        'service': service,
                    }
                    nagios_url = NAGIOS_INSTANCE + '/cmd.cgi'
                    req_output = do_post_request(nagios_url, http_user, http_password, data)
                    nagios_request_validation(req_output, host, service, 'enable_notif')


if args['host']:
    if args['host'] == 'all':
        get_all_hosts_status()
    else:
        print("get specific {} status".format(args['host']))

if args['service_status']:
    selected_service, all_service_status = get_all_service_status()
    do_actions(selected_service, all_service_status)
