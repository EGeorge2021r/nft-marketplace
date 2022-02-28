import os
import json
from hexbytes import HexBytes
from web3 import Web3
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
import pandas as pd

from pinata import get_pins, pin_file_to_ipfs, pin_json_to_ipfs, convert_data_to_json

load_dotenv()

# Define and connect a new Web3 provider
w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_PROVIDER_URI")))

###################################################################################################
# Contract Helper Function:
# 1. Loads the contract once using cache
# 2. Connects to the contract using the contract address and ABI
###################################################################################################

def load_contract(abi_file_path, contract_address):

    # Load the contract ABI
    with open(Path(abi_file_path)) as f:
        contract_abi = json.load(f)

    # Get the contract
    contract = w3.eth.contract(
        address=contract_address,
        abi=contract_abi
    )

    return contract


def pin_artwork(artwork_file):
    # Pin the file to IPFS with Pinata
    ipfs_file_hash = pin_file_to_ipfs(artwork_file.getvalue())

    return ipfs_file_hash

def mint_token(nft_contract):
    transaction = nft_contract.functions.createToken(artwork_uri)
    tx_hash = transaction.transact({"from": address, "gas": 1000000})
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    rich_logs = nft_contract.events.TokenCreated().processReceipt(receipt)
    token_id = rich_logs[0]['args']['itemId']

    return token_id

def create_market_item(marketplace_contract, nft_contract_address, token_id, price, listing_price):
    transaction = marketplace_contract.functions.createMarketItem(
        nft_contract_address, int(token_id), int(price))
    tx_hash = transaction.transact({"from": address, "gas": 1000000, "value": int(listing_price)})
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    rich_logs = marketplace_contract.events.MarketItemCreated().processReceipt(receipt)
    item_id  = rich_logs[0]['args']['itemId']
    return item_id

def buy_nft(marketplace_contract, nft_contract_address, blockhead_id, price_in_wei):
    nft_contract_address = str(nft_contract_address)
    blockhead_id = int(blockhead_id)
    transaction = marketplace_contract.functions.createMarketSale(nft_contract_address, blockhead_id)
    tx_hash = transaction.transact(({"from": address, "gas": 1000000, "value": int(price_in_wei)}))
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    return receipt

def apply_token_uri(row):
    token_id = row["Token Id"]
    transaction = nft_contract.functions.tokenURI(token_id)
    token_uri = transaction.call()
    return token_uri

def get_nfts_for_sale(marketplace_contract):
    transaction = marketplace_contract.functions.fetchMarketItems()
    data = transaction.call()
    unsold_items_df = pd.DataFrame(data)
    unsold_items_df.columns = ['Token Id',  'Contract', 'Blockhead Id', 'Minter', 'Owner', 'Cost', 'Sold']
    unsold_items_df.drop(['Contract'], axis=1, inplace=True)
    unsold_items_df['Token URI'] = unsold_items_df.apply(apply_token_uri, axis=1)

    return unsold_items_df

# Load the contracts
nft_contract_address = os.getenv("NFT_CONTRACT_ADDRESS")
nft_contract = load_contract("./Contracts/Compiled/nft_abi.json", nft_contract_address)
marketplace_contract = load_contract("./Contracts/Compiled/nft_marketplace_abi.json", os.getenv("NFT_MARKET_CONTRACT_ADDRESS"))

st.title("Blockheads' NFT MarketPlace")
st.write("Choose an account to get started")
accounts = w3.eth.accounts
address = st.selectbox("Select Account", options=accounts)
st.markdown("---")



# CREATOR: Upload, mint, and put the item up for sale
st.markdown("## CREATOR SECTION")

st.markdown("### Put your artwork up for sale!")
file = st.file_uploader("Upload Artwork", type=["jpg", "jpeg", "png"])
price = st.text_input("Set the Price (wei)")

if st.button("Register artwork and put it up for sale"):
    try: # to upload the file
        artwork_ipfs_hash = pin_artwork(file)
        artwork_uri = f"{artwork_ipfs_hash}"
    except:
        st.write("File upload failed.")
    else:
        try:
            token_id = mint_token(nft_contract)  # mint the nft
            # TODO: replace the following line with the contract call that gets the listing
            listing_price = 35000000000000000
            item_id = create_market_item(marketplace_contract, nft_contract_address, token_id, price, listing_price)
        except Exception as e:
            st.write("Create token failed.")
            if hasattr(e, 'message'):
                st.write(e.message)
            else:
                st.write(e)
        else:
            st.markdown("**Success!**")
            st.write(f"Token Id: {token_id}  Blockhead Id: {item_id}")
            st.markdown(f"You can view the pinned metadata file with the following IPFS Gateway Link: [Artwork IPFS Gateway Link](https://gateway.pinata.cloud/ipfs/{artwork_ipfs_hash})")
            st.markdown("---")

st.markdown("### Items you have for sale (or sold)")
mp_fetch_items_transaction = marketplace_contract.functions.fetchItemsCreated()
data = mp_fetch_items_transaction.call()
st.table(data)

st.markdown("---")
st.markdown("## BUYER SECTION")

st.markdown("### Items for sale")
data = get_nfts_for_sale(marketplace_contract)
st.table(data)

st.markdown("### Buy an item")
blockhead_id = st.text_input("Enter the Blockhead id for the item you like")
purchase_price = st.text_input("Enter the purchase price.")
if(st.button("Purchase")):
    receipt = buy_nft(marketplace_contract, nft_contract_address, blockhead_id, purchase_price)
    st.write(receipt)


st.markdown("### MISC FUNCTIONS IN TEST")
if st.button("get uri quick and dirty"):
    transaction = nft_contract.functions.tokenURI(2)
    uri = transaction.call()
    st.write(f"Uri: https://gateway.pinata.cloud/ipfs/{uri}")
