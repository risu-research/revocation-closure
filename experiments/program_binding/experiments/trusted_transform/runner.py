"""Unprivileged arbitrary-Python transform runner.

No vault/key access, no output channel other than one brokered socket. Uses Linux
libseccomp after Python starts to deny filesystem opens, new sockets and exec/fork.
This is a research harness, not a general sandbox for native extensions or host-root.
"""
from __future__ import annotations
import argparse, base64, ctypes, errno, hashlib, json, os, socket, sys

MAX_MESSAGE=1_200_000
MAX_OUTPUT=65536

class Abort(RuntimeError):pass

_SOCKET_READER=None

def recv(sock):
    global _SOCKET_READER
    if _SOCKET_READER is None:
        _SOCKET_READER=sock.makefile('rb')
    data=_SOCKET_READER.readline(MAX_MESSAGE+1)
    if not data or len(data)>MAX_MESSAGE or not data.endswith(b'\n'):
        raise Abort('Malformed or closed broker socket')
    return json.loads(data)

def send(sock,msg):
    raw=json.dumps(msg,sort_keys=True,separators=(',',':')).encode()+b'\n'
    if len(raw)>MAX_MESSAGE:raise Abort('message too large')
    sock.sendall(raw)

def install_seccomp():
    """Load default-ALLOW + named prohibitions; fail closed if libseccomp absent."""
    lib=ctypes.CDLL('libseccomp.so.2',use_errno=True)
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    lib.seccomp_rule_add.restype=ctypes.c_int
    lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_load.restype=ctypes.c_int
    lib.seccomp_release.argtypes=[ctypes.c_void_p];lib.seccomp_release.restype=None
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(38,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'no_new_privs failed')
    allow=0x7fff0000; deny=0x00050000|errno.EPERM
    ctx=lib.seccomp_init(allow)
    if not ctx:raise Abort('seccomp_init failed')
    syscalls=[
        'open','openat','openat2','creat',
        'socket','socketpair','connect','bind','listen','accept','accept4',
        'fork','vfork','clone','clone3','execve','execveat','ptrace',
        'process_vm_readv','process_vm_writev','pidfd_getfd',
        'mount','umount2','pivot_root','chroot','setns','unshare',
        'chmod','fchmod','fchmodat','chown','fchown','fchownat',
        'link','linkat','symlink','symlinkat','rename','renameat','renameat2',
        'unlink','unlinkat','mkdir','mkdirat','rmdir',
        'setuid','setgid','setresuid','setresgid','setreuid','setregid',
        'capset','bpf','keyctl','add_key','request_key','io_uring_setup',
        'prctl','seccomp','kill','tkill','tgkill',
        'memfd_create','userfaultfd','pidfd_open'
    ]
    try:
        for name in syscalls:
            nr=lib.seccomp_syscall_resolve_name(name.encode())
            if nr<0:continue
            err=lib.seccomp_rule_add(ctx,deny,nr,0)
            if err!=0:raise Abort('seccomp rule failed '+name+' '+str(err))
        err=lib.seccomp_load(ctx)
        if err!=0:raise Abort('seccomp_load failed '+str(err))
    finally:lib.seccomp_release(ctx)
    # Canary assertions of applied restrictions using pre-imported modules.
    try:
        os.open('/etc/passwd',os.O_RDONLY)
    except PermissionError:pass
    else:raise Abort('open syscall not denied')
    try:
        socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except PermissionError:pass
    else:raise Abort('socket syscall not denied')
    return True

def run(fd:int,expected_uid:int):
    if os.geteuid()!=expected_uid or os.geteuid()==0:raise Abort('wrong worker identity')
    # Only inherited IPC is needed. No raw vault descriptors enter this process.
    sock=socket.socket(fileno=fd)
    init=recv(sock)
    if set(init)!={'cmd','program_b64','program_sha256','run_id'} or init['cmd']!='init':raise Abort('bad init')
    program=base64.b64decode(init['program_b64'],validate=True)
    if len(program)>32768 or hashlib.sha256(program).hexdigest()!=init['program_sha256']:
        raise Abort('program byte integrity mismatch')
    # Bytecode compiled BEFORE syscall restrictions, with no user-controlled imports.
    compiled=compile(program.decode('utf-8'),'<trusted_transform_program>','exec')
    # Interpreter-side output streams must not bypass the recipient.
    null=os.open('/dev/null',os.O_WRONLY)
    os.dup2(null,1);os.dup2(null,2);os.close(null)
    if not install_seccomp():raise Abort('sandbox did not start')
    send(sock,{'cmd':'ready','seccomp_loaded':True})
    emitted=[]
    def rpc(msg):
        send(sock,msg)
        answer=recv(sock)
        if not isinstance(answer,dict) or set(answer)!={'ok','result'}:
            raise Abort('bad broker reply')
        if not answer['ok']:raise Abort(str(answer['result']))
        return answer['result']
    def read(source_id):
        if not isinstance(source_id,str):raise Abort('Invalid source id')
        obj=rpc({'cmd':'read','source_id':source_id})
        raw=base64.b64decode(obj['bytes_b64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=obj['sha256']:
            raise Abort('broker read digest mismatch')
        return raw
    def parent(artifact_id):
        if not isinstance(artifact_id,str):raise Abort('Invalid parent id')
        return rpc({'cmd':'parent','artifact_id':artifact_id})['artifact_id']
    def emit(raw):
        if type(raw) is not bytes or len(raw)>MAX_OUTPUT or emitted:
            raise Abort('Output must be one bytes value <=64KB')
        emitted.append(raw)
    # Arbitrary Python code executes under distinct UID with restricted syscalls.
    # Python language is NOT considered a security sandbox; the OS boundary is.
    env={'read':read,'parent':parent,'emit':emit,'__name__':'__trusted_transform__'}
    try:
        exec(compiled,env,env)
        if len(emitted)!=1:raise Abort('No output emitted')
        send(sock,{'cmd':'complete','output_b64':base64.b64encode(emitted[0]).decode()})
        response=recv(sock)
        if response!={'ok':True,'result':'SEALED'}:raise Abort('Broker refused completion')
    except BaseException as e:
        # Runtime never signs error/partial results.
        try:send(sock,{'cmd':'fail','error_type':type(e).__name__})
        except BaseException:pass
        raise
    finally:sock.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fd',required=True,type=int)
    parser.add_argument('--uid',required=True,type=int)
    a=parser.parse_args();run(a.fd,a.uid)
