"""Source of MLMoney's Win32 MSG handler; python money_keys.py prints its Lua hex."""
BASE = 0x03fc9300  # after MLNews; still in the checked zero run ending at 03fc9da0
SIZE = 0x140
STEP, WAGE, RATIO, HALF = (BASE + SIZE - 24 + n for n in (0,4,8,16))
SITE = 0x02bd2663  # main pump loads DispatchMessageW into ebx before its message loop
OLD = bytes.fromhex('8b1da0787d04')
NEW = b'\xbb' + BASE.to_bytes(4, 'little') + b'\x90'
SOURCE = f'''
    mov ecx, [esp+4]
    cmp dword ptr [ecx+4], 0x100
    jne dispatch
    mov eax, [ecx+8]
    sub eax, 0x75
    cmp eax, 1
    ja dispatch
    test byte ptr [ecx+15], 0x40
    jnz dispatch
    push esi
    mov esi, ecx
    call dword ptr [0x047d7948]
    test eax,eax
    jz done
    cmp eax, [esi]
    jne done
    mov ecx, [0x0264f3e8]
    test ecx, ecx
    jz done
    mov eax, [ecx+0x20]
    cmp eax, 0x13
    je career
    cmp eax, 0x28
    jne done
career:
    mov ecx, [0x026503e0]
    test ecx, ecx
    jz done
    mov ecx, [ecx+0x30]
    test ecx, ecx
    jz done
    add ecx, 0xdddfc4
    mov eax, [ecx]
    mov edx, [ecx+24]
    cmp eax, 99999999
    ja done
    cmp edx, 99999999
    ja done
    cmp byte ptr [esi+8], 0x75
    jne to_transfer
    mov esi, [{STEP}]
    cmp esi, eax
    cmova esi, eax
    sub eax, esi
    cvtsi2sd xmm0, esi
    divsd xmm0, qword ptr [{RATIO}]
    addsd xmm0, qword ptr [{HALF}]
    cvttsd2si esi, xmm0
    test esi, esi
    jz done
    add edx, esi
    cmp edx, 99999999
    ja done
    jmp store
 to_transfer:
    mov esi, [{WAGE}]
    cmp esi, edx
    cmova esi, edx
    sub edx, esi
    cvtsi2sd xmm0, esi
    mulsd xmm0, qword ptr [{RATIO}]
    addsd xmm0, qword ptr [{HALF}]
    cvttsd2si esi, xmm0
    add eax, esi
    cmp eax, 99999999
    ja done
store:
    mov [ecx], eax
    mov [ecx+24], edx
done:
    pop esi
dispatch:
    jmp dword ptr [0x047d78a0]
'''


def code():
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    b = bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(SOURCE, BASE)[0])
    assert len(b) <= STEP-BASE
    return b


if __name__ == '__main__':
    print(code().hex())
