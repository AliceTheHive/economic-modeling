import networksim
from casper import Validator
from ethereum.parse_genesis_declaration import mk_basic_state
from ethereum.config import Env
from ethereum.casper_utils import casper_config, get_casper_code, get_rlp_decoder_code, \
    get_casper_ct, RandaoManager, generate_validation_code, get_hash_without_ed_code
from ethereum.utils import sha3, privtoaddr
from ethereum.transactions import Transaction
from ethereum.state_transition import apply_transaction

from ethereum.slogging import LogRecorder, configure_logging, set_level
# config_string = ':info,eth.vm.log:trace,eth.vm.op:trace,eth.vm.stack:trace,eth.vm.exit:trace,eth.pb.msg:trace,eth.pb.tx:debug'
# config_string = ':info,eth.vm.log:trace'
# configure_logging(config_string=config_string)

n = networksim.NetworkSimulator()
n.time = 2
print 'Generating keys'
keys = [sha3(str(i)) for i in range(20)]
print 'Initializing randaos'
randaos = [RandaoManager(sha3(k)) for k in keys]
deposit_sizes = [128] * 15 + [256] * 5

print 'Creating genesis state'
s = mk_basic_state({}, None, env=Env(config=casper_config))
s.gas_limit = 10**9
s.prev_headers[0].timestamp = 2
s.timestamp = 2
s.prev_headers[0].difficulty = 1
s.block_difficulty = 1
s.set_code(casper_config['CASPER_ADDR'], get_casper_code())
s.set_code(casper_config['RLP_DECODER_ADDR'], get_rlp_decoder_code())
s.set_code(casper_config['HASH_WITHOUT_BLOOM_ADDR'], get_hash_without_ed_code())
ct = get_casper_ct()
# Add all validators
for k, r, ds in zip(keys, randaos, deposit_sizes):
    a = privtoaddr(k)
    # Leave 1 eth to pay txfees
    s.set_balance(a, (ds + 1) * 10**18)
    t = Transaction(0, 0, 10**8, casper_config['CASPER_ADDR'], ds * 10**18, ct.encode('deposit', [generate_validation_code(a), r.get(9999)])).sign(k)
    success, gas, logs = apply_transaction(s, t)
s.commit()
g = s.to_snapshot()
print 'Genesis state created'

validators = [Validator(g, k, n, Env(config=casper_config)) for k in keys]
n.agents = validators
n.generate_peers()

for i in range(100000):
    # print 'ticking'
    n.tick()
    if i % 100 == 0:
        print 'Validator heads:', [v.chain.head.header.number if v.chain.head else None for v in validators]
