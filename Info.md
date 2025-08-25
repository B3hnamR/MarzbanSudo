MarzbanAPI
 0.8.4 
OAS 3.1
/openapi.json
Unified GUI Censorship Resistant Solution Powered by Xray


POST
/api/admin/token
Admin Token


GET
/api/admin
Get Current Admin



POST
/api/admin
Create Admin



PUT
/api/admin/{username}
Modify Admin



DELETE
/api/admin/{username}
Remove Admin



GET
/api/admins
Get Admins



POST
/api/admin/{username}/users/disable
Disable All Active Users



POST
/api/admin/{username}/users/activate
Activate All Disabled Users



POST
/api/admin/usage/reset/{username}
Reset Admin Usage



GET
/api/admin/usage/{username}
Get Admin Usage


Core


GET
/api/core
Get Core Stats



POST
/api/core/restart
Restart Core



GET
/api/core/config
Get Core Config



PUT
/api/core/config
Modify Core Config


Node


GET
/api/node/settings
Get Node Settings



POST
/api/node
Add Node



GET
/api/node/{node_id}
Get Node



PUT
/api/node/{node_id}
Modify Node



DELETE
/api/node/{node_id}
Remove Node



GET
/api/nodes
Get Nodes



POST
/api/node/{node_id}/reconnect
Reconnect Node



GET
/api/nodes/usage
Get Usage


Subscription


GET
/sub4me/{token}/
User Subscription


GET
/sub4me/{token}/info
User Subscription Info


GET
/sub4me/{token}/usage
User Get Usage


GET
/sub4me/{token}/{client_type}
User Subscription With Client Type

System


GET
/api/system
Get System Stats



GET
/api/inbounds
Get Inbounds



GET
/api/hosts
Get Hosts



PUT
/api/hosts
Modify Hosts


User Template


POST
/api/user_template
Add User Template



GET
/api/user_template
Get User Templates



GET
/api/user_template/{template_id}
Get User Template Endpoint



PUT
/api/user_template/{template_id}
Modify User Template



DELETE
/api/user_template/{template_id}
Remove User Template


User


POST
/api/user
Add User



GET
/api/user/{username}
Get User



PUT
/api/user/{username}
Modify User



DELETE
/api/user/{username}
Remove User



POST
/api/user/{username}/reset
Reset User Data Usage



POST
/api/user/{username}/revoke_sub
Revoke User Subscription



GET
/api/users
Get Users



POST
/api/users/reset
Reset Users Data Usage



GET
/api/user/{username}/usage
Get User Usage



POST
/api/user/{username}/active-next
Active Next Plan



GET
/api/users/usage
Get Users Usage



PUT
/api/user/{username}/set-owner
Set Owner



GET
/api/users/expired
Get Expired Users



DELETE
/api/users/expired
Delete Expired Users


