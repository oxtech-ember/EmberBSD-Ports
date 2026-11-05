#[cfg(all(feature="salsa",feature="chacha",feature="seal",feature="serde",feature="os_rng"))]
mod runtime {
// RustCrypto upstream published NaCl and PHP Sodium compatibility vectors.
use crypto_secretbox::{XSalsa20Poly1305, aead::{Aead, KeyInit}};
use crypto_box::{SalsaBox, PublicKey, SecretKey};
use crypto_secretbox::aead::{AeadInOut, inout::InOutBuf};
fn decode(s: &str) -> Vec<u8> { (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2],16).unwrap()).collect() }
pub fn run() {
    let key: [u8;32] = decode("1b27556473e985d462cd51197a9a46c76009549eac6474f206c4ee0844f68389").try_into().unwrap();
    let nonce: [u8;24] = decode("69696ee955b62b73cd62bda875fc73d68219e0036b7a0b37").try_into().unwrap();
    let msg=decode("be075fc53c81f2d5cf141316ebeb0c7b5228c52a4c62cbd44b66849b64244ffce5ecbaaf33bd751a1ac728d45e6c61296cdc3c01233561f41db66cce314adb310e3be8250c46f06dceea3a7fa1348057e2f6556ad6b1318a024a838f21af1fde048977eb48f59ffd4924ca1c60902e52f0a089bc76897040e082f937763848645e0705");
    let expected=decode("f3ffc7703f9400e52a7dfb4b3d3305d98e993b9f48681273c29650ba32fc76ce48332ea7164d96a4476fb8c531a1186ac0dfc17c98dce87b4da7f011ec48c97271d2c20f9b928fe2270d6fb863d51738b48eeee314a7cc8ab932164548e526ae90224368517acfeabd6bb3732bc0e9da99832b61ca01b6de56244a9e88d5f9b37973f622a43d14a6599b1f654cb45a74e355a5");
    macro_rules! check_out_of_place {
        ($cipher:expr, $expected:expr) => {{
            let expected = $expected;
            let mut output = vec![0xa5; msg.len()];
            let tag = $cipher.encrypt_inout_detached((&nonce).into(), b"", InOutBuf::new(&msg, &mut output).unwrap()).unwrap();
            assert_eq!(tag.as_slice(), &expected[..16]);
            assert_eq!(output, expected[16..]);
            let mut decoded = vec![0x5a; msg.len()];
            $cipher.decrypt_inout_detached((&nonce).into(), b"", InOutBuf::new(&output, &mut decoded).unwrap(), &tag).unwrap();
            assert_eq!(decoded, msg);
            let mut invalid = tag.clone(); invalid[0] ^= 1;
            let mut untouched = vec![0x3c; msg.len()];
            assert!($cipher.decrypt_inout_detached((&nonce).into(), b"", InOutBuf::new(&output, &mut untouched).unwrap(), &invalid).is_err());
            assert_eq!(untouched, vec![0x3c; msg.len()]);
        }};
    }
    let cipher=XSalsa20Poly1305::new((&key).into());
    check_out_of_place!(cipher, &expected);
    let ciphertext=cipher.encrypt((&nonce).into(), msg.as_slice()).unwrap();
    assert_eq!(ciphertext,expected); assert_eq!(cipher.decrypt((&nonce).into(),ciphertext.as_slice()).unwrap(),msg);
    let mut tampered=ciphertext.clone();tampered[0]^=1;assert!(cipher.decrypt((&nonce).into(),tampered.as_slice()).is_err());
    let alice: [u8;32] = decode("68f208412d8dd5db9d0c6d18512e86f0ec75665ab841372d57b042b27ef89d4c").try_into().unwrap();
    let bob: [u8;32] = decode("e8980c86e032f1eb2975052e8d65bddd15c3b59641174ec9678a53789d92c754").try_into().unwrap();
    let cipher=SalsaBox::new(&PublicKey::from(bob),&SecretKey::from(alice));
    assert_eq!(cipher.encrypt((&nonce).into(),msg.as_slice()).unwrap(),decode("c03f27d188ef650cd12936913137bb17ed4c98c2648939e2e1d2e855470a7b8c632cabfd5ab3b3c2d313dc8c9ecf5da173e1f9c318cdef1dced6d2519e695085e6b5c401a2bd5331442986c7076d412625497c4cb2fd94c6f103961033b2c930d7e82e0341f29d3879bd6ab9d881ea3a1f365d634e653c6e171aac7fc1e76934d23be6f04a54010808dbf0f9bd30f63b68d026"));
    let cipher = crypto_secretbox::XChaCha20Poly1305::new((&key).into());
    let enc = cipher.encrypt((&nonce).into(), msg.as_slice()).unwrap();
    assert_eq!(enc, decode("0c61fcffbc3fc8d3aa7464b91ab35374bf8af3198585e55d9cb07edcd1e5a69526547fbd0f2c642e9ee96e19462031f1032f1cd862bb952900103c06ac16344d7f9c9df0feaaf5a733dea7ea2df70a619936fcc5501de75c5d112e8abd7573c461ada29ec016d131aa557804320011ff6d94092581ceea1bad3cf0d651938802ca867cd52bbe50c2da1161cb09514407609920"));
    check_out_of_place!(cipher, &enc);
    assert_eq!(cipher.decrypt((&nonce).into(), enc.as_slice()).unwrap(), msg);
    let cipher = crypto_box::ChaChaBox::new(&PublicKey::from(bob), &SecretKey::from(alice));
    assert_eq!(cipher.encrypt((&nonce).into(), msg.as_slice()).unwrap(), decode("0cd5ed093de698c8e410d0d451df2f5283057376b947b9b7392b956e5d675f309218acce8cf85f6cf6a9e2e09ef8c5b0f97c661ee21b1b3418be566692634056a92b4034d5d0cf14c52420a488b7f0da0c5740dfc6b85397d3a8f679e84303e8d3f8b048abdb2dd79183b0a62683a1bc2a527fc9b82c5ffac4a684bcfeadfdcd28930b2dbe597f4716a658ccfca5b44049e06c"));
    let mut rng = crypto_box::aead::rand_core::UnwrapErr(crypto_box::aead::common::getrandom::SysRng);
    let sk = SecretKey::generate(&mut rng);
    let pk = sk.public_key();
    let sealed = pk.seal(&mut rng, msg.as_slice()).unwrap();
    assert_eq!(sk.unseal(&sealed).unwrap(), msg);
    let json = serde_json::to_string(&pk).unwrap();
    let roundtrip: PublicKey = serde_json::from_str(&json).unwrap();
    assert_eq!(roundtrip, pk);
    let mut wiped = SecretKey::from(alice);
    zeroize::Zeroize::zeroize(&mut wiped);
    assert_eq!(wiped.as_bytes(), &[0; 32]);
    println!("salsa, chacha, seal, serde, OS RNG and zeroize vectors: PASS");
}

}
#[cfg(all(feature="salsa",feature="chacha",feature="seal",feature="serde",feature="os_rng"))]
fn main() { runtime::run(); }
#[cfg(not(all(feature="salsa",feature="chacha",feature="seal",feature="serde",feature="os_rng")))]
fn main() {}
