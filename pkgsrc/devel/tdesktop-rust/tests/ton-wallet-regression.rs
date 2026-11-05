// Public upstream test mnemonic, never an account or network operation.
use std::str::FromStr;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use ton::block_tlb::{CommonMsgInfo, Msg};
use ton::ton_core::cell::TonCell;
use ton::ton_core::traits::tlb::TLB;
use ton::ton_core::types::TonAddress;
use ton::ton_wallet::{Mnemonic, TonWallet, WalletVersion, WalletExtMsgBody,
    WalletInternalSignedBody, WALLET_SUBWALLET_ID_DEFAULT};

const PHRASE: &str = "fancy carpet hello mandate penalty trial consider property top vicious exit rebuild tragic profit urban major total month holiday sudden rib gather media vicious";
const PHRASE_V5: &str = "section garden tomato dinner season dice renew length useful spin trade intact use universe what post spike keen mandate behind concert egg doll rug";

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let key = Mnemonic::from_str(PHRASE, None)?.to_key_pair()?;
    let key_v5 = Mnemonic::from_str(PHRASE_V5, None)?.to_key_pair()?;
    for (version, expected) in [
        (WalletVersion::V3R1, "EQBiMfDMivebQb052Z6yR3jHrmwNhw1kQ5bcAUOBYsK_VPuK"),
        (WalletVersion::V3R2, "EQA-RswW9QONn88ziVm4UKnwXDEot5km7GEEXsfie_0TFOCO"),
        (WalletVersion::V4R2, "EQCDM_QGggZ3qMa_f3lRPk4_qLDnLTqdi6OkMAV2NB9r5TG3"),
    ] { assert_eq!(TonWallet::new(version, key.clone())?.address, TonAddress::from_str(expected)?); }
    assert_eq!(TonWallet::new(WalletVersion::V5R1, key_v5)?.address,
        TonAddress::from_str("UQDv2YSmlrlLH3hLNOVxC8FcQf4F9eGNs4vb2zKma4txo6i3")?);
    let wallet = TonWallet::new(WalletVersion::Wallet, key.clone())?;
    let explicit = TonWallet::new_with_params(WalletVersion::Wallet, key.clone(), 0, WALLET_SUBWALLET_ID_DEFAULT)?;
    assert_eq!(wallet.address, explicit.address);
    assert_eq!(wallet.wallet_id, WALLET_SUBWALLET_ID_DEFAULT);
    let action = TonCell::builder().build()?;
    let unsigned = wallet.create_ext_in_body_with_modes(1_900_000_000, 17, vec![action.clone()], vec![3])?;
    let signed = wallet.sign_ext_in_body(&unsigned)?;
    let (body, signature) = WalletExtMsgBody::read_signed(&mut signed.parser())?;
    assert_eq!(body.wallet_id, WALLET_SUBWALLET_ID_DEFAULT);
    assert_eq!(body.msg_seqno, 17); assert_eq!(body.msgs_modes, vec![3]); assert_eq!(body.msgs, vec![action.clone()]);
    let verify = VerifyingKey::from_bytes(&key.public_key)?;
    verify.verify(unsigned.cell_hash()?.as_slice(), &Signature::from_slice(&signature)?)?;
    let internal = wallet.create_internal_signed_msg_with_modes(vec![action.clone()], vec![3], 17, 1_900_000_000, true)?;
    let msg = Msg::<TonCell>::from_cell(&internal)?;
    assert!(matches!(msg.info, CommonMsgInfo::Int(_))); assert!(msg.init.is_some());
    let (body, signature) = WalletInternalSignedBody::read_signed(&mut msg.body.value.parser())?;
    assert_eq!(body.wallet_id, WALLET_SUBWALLET_ID_DEFAULT); assert_eq!(body.msg_seqno, 17);
    assert_eq!(body.msgs_modes, vec![3]); assert_eq!(body.msgs, vec![action]);
    verify.verify(body.to_cell()?.cell_hash()?.as_slice(), &Signature::from_slice(&signature)?)?;
    println!("Wallet defaults, V3/V4/V5 upstream addresses and signed internal/external requests: PASS");
    Ok(())
}
