# Copyright (c) 2017 David Preece, All rights reserved.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from awsornot.kv import KeyValue
from awsornot.kvread import KeyValueRead

kv = KeyValue('test_keystore')
kv.put_parameter(Name="test", Description="Test Data", Type="String", Value="testing123", Overwrite=True)
param = kv.get_parameter(Name="test")
if param['Parameter']['Value'] != "testing123":
    print("Server failed")

# kv.put_parameter(Name="toobig", Description="Too Big", Type="String", Value="-".join([str(n) for n in range(0, 20000)]),
#                  Overwrite=True)

kvr = KeyValueRead()
param = kvr.get_parameter(Name="test")
if param['Parameter']['Value'] != "testing123":
    print("Client failed")

kv.stop()
