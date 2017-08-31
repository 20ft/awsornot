# AWS or Not

These are a set of classes for logging and/or kv value storage that work 'identically' whether or not they are currently running on AWS (EC2, whatever). By 'identically' I mean that when running on AWS, the platform's native features are used (in this case CloudWatch Logs and the SSM Parameter store) with no code changes.

This is Python 3 code and I imagine it runs under Python 2 but, well, maybe not.

Your best bet for installation is ```pip3 install awsornot```.

## awsornot.LogHandler

Construct the handler with CloudWatch "group" and "stream" parameters - the logs themselves are delivered asynchronously so your app doesn't have to wait for AWS to do it's thing. Note that you can optionally supply a blacklist of strings which, if occurring in an about-to-be-logged line will prevent the line from being logged.
Since the logger runs a background thread it needs to be explicitly stopped (because otherwise the thread holds a reference to its parent). I like to put this in a 'finally' clause. 
So, for example:
```Python
log = awsornot.LogHandler('group', 'stream', ['Starting new HTTP connection'])
try:
    some.things()
finally:
    log.stop()
```

## awsornot.KeyValue

The KV store is **heavily biased around bootstrapping** child instances in a client/server style application. When used under AWS it thinly wraps the SSM Parameter Store and on bare metal writes a zero-subtlety file containing the entire database on every change. The put_parameter and get_parameter methods are drop-in compatible with the methods on boto3's ssm client but only return the Parameter->Value->whatever object tree. For the majority of cases the upshot of this is that boto code that says `x.get_parameter('param')['Parameter']['Value']` will do the same thing.
When not running as part of AWS the class creates a webserver, running (default) on port 1026 that provides a read-only view of the parameter store. Obviously this is not a great place to store secrets or, if you do, you need to have your firewalling sorted out.
```
kv = awsornot.KeyValue()

kv.put_parameter(
        Name="param-name",
        Description="Some parameter that needs storing and publishing to a wider audience",
        Type="String",
        Value="FooBar",
        Overwrite=True
)

print(kv.get_parameter(Name='param-name')['Parameter']['Value'])
```

## awsornot.KeyValueRead

This is the read-only client to work with KeyValue store. Currently it needs starting up with the fqdn/ip of the KeyValue server - which doesn't get used if running under AWS. I'm sure there's something more elegant that can be done with mDNS or whatever but that's just not how it is.
Note that due to the 'bootstrap' nature of the KV store, updates are not pushed to the clients and - in fact - all that happens is it pulls the entire KV store off the port 1026 server and just accesses that. If you want more, use a proper database :)
```
kv = awsornot.KeyValueRead('server.local')

print(kv.get_parameter(Name='param-name')['Parameter']['Value'])
```
