// RustCrypto upstream published NaCl and PHP Sodium compatibility vectors.
use crypto_secretbox::{XSalsa20Poly1305, aead::{Aead, KeyInit}};
use crypto_box::{SalsaBox, PublicKey, SecretKey};
fn decode(s: &str) -> Vec<u8> { (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2],16).unwrap()).collect() }
fn main() {
    let key: [u8;32] = decode("1b27556473e985d462cd51197a9a46c76009549eac6474f206c4ee0844f68389").try_into().unwrap();
    let nonce: [u8;24] = decode("69696ee955b62b73cd62bda875fc73d68219e0036b7a0b37").try_into().unwrap();
    let msg=decode("be075fc53c81f2d5cf141316ebeb0c7b5228c52a4c62cbd44b66849b64244ffce5ecbaaf33bd751a1ac728d45e6c61296cdc3c01233561f41db66cce314adb310e3be8250c46f06dceea3a7fa1348057e2f6556ad6b1318a024a838f21af1fde048977eb48f59ffd4924ca1c60902e52f0a089bc76897040e082f937763848645e0705");
    let expected=decode("f3ffc7703f9400e52a7dfb4b3d3305d98e993b9f48681273c29650ba32fc76ce48332ea7164d96a4476fb8c531a1186ac0dfc17c98dce87b4da7f011ec48c97271d2c20f9b928fe2270d6fb863d51738b48eeee314a7cc8ab932164548e526ae90224368517acfeabd6bb3732bc0e9da99832b61ca01b6de56244a9e88d5f9b37973f622a43d14a6599b1f654cb45a74e355a5");
    let cipher=XSalsa20Poly1305::new((&key).into());
    let ciphertext=cipher.encrypt((&nonce).into(), msg.as_slice()).unwrap();
    assert_eq!(ciphertext,expected); assert_eq!(cipher.decrypt((&nonce).into(),ciphertext.as_slice()).unwrap(),msg);
    let mut tampered=ciphertext.clone();tampered[0]^=1;assert!(cipher.decrypt((&nonce).into(),tampered.as_slice()).is_err());
    let alice: [u8;32] = decode("68f208412d8dd5db9d0c6d18512e86f0ec75665ab841372d57b042b27ef89d4c").try_into().unwrap();
    let bob: [u8;32] = decode("e8980c86e032f1eb2975052e8d65bddd15c3b59641174ec9678a53789d92c754").try_into().unwrap();
    let cipher=SalsaBox::new(&PublicKey::from(bob),&SecretKey::from(alice));
    assert_eq!(cipher.encrypt((&nonce).into(),msg.as_slice()).unwrap(),decode("c03f27d188ef650cd12936913137bb17ed4c98c2648939e2e1d2e855470a7b8c632cabfd5ab3b3c2d313dc8c9ecf5da173e1f9c318cdef1dced6d2519e695085e6b5c401a2bd5331442986c7076d412625497c4cb2fd94c6f103961033b2c930d7e82e0341f29d3879bd6ab9d881ea3a1f365d634e653c6e171aac7fc1e76934d23be6f04a54010808dbf0f9bd30f63b68d026"));
    println!("RustCrypto secretbox and box upstream vectors: PASS");
}
