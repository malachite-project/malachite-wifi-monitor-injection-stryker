from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit(f'Usage: {sys.argv[0]} /path/to/patched/gl_kal.c')

source = Path(sys.argv[1])
text = source.read_text()
start = text.index('u_int8_t kalProcessRadiotap(')
body = text[start:text.index('\nvoid kalSetPacketDev(', start)]
headers = """
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <sys/types.h>

#define FALSE 0
#define TRUE 1
#define kalMemZero(buf, n) memset(buf, 0, n)
struct sk_buff {
    unsigned char storage[256];
    unsigned char *data;
    unsigned int tail;
    unsigned int len;
    unsigned int data_len;
};
static int skb_is_nonlinear(const struct sk_buff *skb) { return skb->data_len != 0; }
static unsigned int skb_headroom(const struct sk_buff *skb) { return skb->data - skb->storage; }
static unsigned char *skb_end_pointer(struct sk_buff *skb) { return skb->storage + sizeof(skb->storage); }
static void skb_push(struct sk_buff *skb, unsigned int n) {
    assert(n <= skb_headroom(skb));
    skb->data -= n;
    skb->len += n;
}
static void skb_reset_tail_pointer(struct sk_buff *skb) { skb->tail = skb_headroom(skb); }
static void skb_trim(struct sk_buff *skb, unsigned int n) {
    if (skb->len > n) {
        skb->len = n;
        skb->tail = skb_headroom(skb) + n;
    }
}
static void skb_put(struct sk_buff *skb, unsigned int n) {
    assert(n <= sizeof(skb->storage) - skb->tail);
    skb->tail += n;
    skb->len += n;
}
"""
tests = """
int main(void) {
    uint8_t *data = 0;
    struct sk_buff skb = {0};
    assert(!kalProcessRadiotap(0, &data, 1, 1));
    for (unsigned int headroom = 0; headroom <= 128; headroom++) {
        for (unsigned int header = 0; header <= 129; header++) {
            for (unsigned int frame = 0; frame <= 257; frame++) {
                skb.data = skb.storage + headroom;
                skb.len = 0;
                skb.tail = headroom;
                skb.data_len = 0;
                memset(skb.storage, 0xa5, sizeof(skb.storage));
                data = 0;
                int accepted = kalProcessRadiotap(&skb, &data, header, frame);
                int expected = header <= headroom && frame <= sizeof(skb.storage) - headroom;
                assert(accepted == expected);
                if (accepted) {
                    assert(data == skb.storage + headroom - header);
                    assert(skb.len == header + frame);
                    assert(skb.tail == headroom + frame);
                    for (unsigned int i = 0; i < header; i++) assert(data[i] == 0);
                    for (unsigned int i = 0; i < frame; i++) assert(data[header + i] == 0xa5);
                } else {
                    assert(skb.data == skb.storage + headroom && data == 0);
                    assert(skb.tail == headroom && skb.len == 0);
                }
            }
        }
    }
    skb.data = skb.storage + 128;
    skb.data_len = 1;
    assert(!kalProcessRadiotap(&skb, &data, 32, 32));
}
"""
with tempfile.TemporaryDirectory() as temp:
    c = Path(temp) / 'radiotap-buffer.c'
    binary = c.with_suffix('')
    c.write_text(headers + body + tests)
    subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror', '-O1', '-fsanitize=address,undefined',
                    '-no-pie', str(c), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('PASS extracted kalProcessRadiotap with 4,326,660 size combinations, null and nonlinear cases')
