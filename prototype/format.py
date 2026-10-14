"""Pack/unpack the 92-byte puzzle record format used by
sudoku_problem_{otegaru,easy,normal,hard}.dat in Brain Training.

struct SudokuPuzzleRecord {      // 92 bytes (0x5C)
    u16 index_a;                 // +0x00 puzzle index, duplicated
    u16 index_b;                 // +0x02
    u8  type_flag;                // +0x04 0x00 = normal puzzle, 0x02 = tutorial/demo slot
    u8  flag1;                    // +0x05 always 0x01
    u8  flag2;                    // +0x06 always 0x01
    nibble given[81];              // +0x07..+0x2F (41 bytes), 0 = blank cell
    nibble solution[81];           // +0x30..+0x58 (41 bytes), 1-9
    u8  padding[3];                // +0x59..+0x5B
};
"""

RECORD_SIZE = 92
GIVEN_OFFSET = 7
GIVEN_BYTES = 41
SOLUTION_OFFSET = 48
SOLUTION_BYTES = 41


def _pack_nibbles(cells):
    """81 cell values (0-9) -> 41 bytes of packed nibbles (last nibble unused/zero)."""
    out = bytearray(41)
    for i in range(81):
        byte_idx, is_low = divmod(i, 2)
        if is_low == 0:
            out[byte_idx] |= (cells[i] & 0xF) << 4
        else:
            out[byte_idx] |= cells[i] & 0xF
    return bytes(out)


def _unpack_nibbles(data):
    """41 bytes of packed nibbles -> 81 cell values (0-9)."""
    out = []
    for byte in data:
        out.append(byte >> 4)
        out.append(byte & 0xF)
    return out[:81]


def pack_record(index, given, solution, type_flag=0):
    assert len(given) == 81 and len(solution) == 81
    rec = bytearray(RECORD_SIZE)
    rec[0] = index & 0xFF
    rec[1] = (index >> 8) & 0xFF
    rec[2] = index & 0xFF
    rec[3] = (index >> 8) & 0xFF
    rec[4] = type_flag
    rec[5] = 1
    rec[6] = 1
    rec[GIVEN_OFFSET:GIVEN_OFFSET + GIVEN_BYTES] = _pack_nibbles(given)
    rec[SOLUTION_OFFSET:SOLUTION_OFFSET + SOLUTION_BYTES] = _pack_nibbles(solution)
    # rec[89:92] stays zero (padding)
    return bytes(rec)


def unpack_record(rec):
    assert len(rec) == RECORD_SIZE
    index = rec[0] | (rec[1] << 8)
    type_flag = rec[4]
    given = _unpack_nibbles(rec[GIVEN_OFFSET:GIVEN_OFFSET + GIVEN_BYTES])
    solution = _unpack_nibbles(rec[SOLUTION_OFFSET:SOLUTION_OFFSET + SOLUTION_BYTES])
    return index, type_flag, given, solution


def load_dat(path):
    """Returns a list of (index, type_flag, given, solution) tuples."""
    data = open(path, "rb").read()
    assert len(data) % RECORD_SIZE == 0, f"{path}: size {len(data)} is not a multiple of {RECORD_SIZE}"
    n = len(data) // RECORD_SIZE
    return [unpack_record(data[i * RECORD_SIZE:(i + 1) * RECORD_SIZE]) for i in range(n)]


def save_dat(path, records):
    """records: list of (given, solution) or (given, solution, type_flag) tuples."""
    with open(path, "wb") as f:
        for i, rec in enumerate(records):
            if len(rec) == 2:
                given, solution = rec
                type_flag = 0
            else:
                given, solution, type_flag = rec
            f.write(pack_record(i, given, solution, type_flag))
