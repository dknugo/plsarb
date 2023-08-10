import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests

API_URL = "https://apiv5.paraswap.io"
CHAINS_LIST = [
                # [1, 'Ethereum'],
                [42161, 'Arbitrum']
            ]

DEF_TAKER = "ARB"
DEF_MAKER = "plsARB"

TOKENS_LIST = [
    ['0x7a5D193fE4ED9098F7EAdC99797087C96b002907', 'plsARB'],
    ['0x912CE59144191C1204E64559FE8253a0e49E6548', 'ARB']
]


@st.cache_data
def get_tokens(chain_id):
    url = API_URL + '/tokens/' + str(chain_id)
    res = requests.get(url)
    if res.status_code == 200:
        if 'tokens' in res.json():
            if len(res.json()['tokens']) > 0:
                return pd.DataFrame(res.json()['tokens'])[['address', 'symbol']]
        st.info(f'Token list empty')
        return pd.DataFrame()
    else:
        st.error(f'Error fetching token list: {res.status_code}, {res.json()["error"]}')
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_limit_orders(chain_id, maker_asset, taker_asset):
    url = API_URL + '/ft/orders/' + str(chain_id) + '/orderbook/?makerAsset=' + maker_asset + '&takerAsset=' + taker_asset
    res = requests.get(url)
    if res.status_code == 200:
        if 'orders' in res.json():
            if len(res.json()['orders']) > 0:
                res_df = pd.DataFrame(res.json()['orders'])
                return res_df[res_df.state == 'PENDING']
        st.info(f'No orders found')
        return pd.DataFrame()
    else:
        st.error(f'Error fetching orders: {res.status_code}, {res.json()["error"]}')
        return pd.DataFrame()

def click_refresh():
    get_limit_orders.clear()

with st.sidebar:
    
    chains_df = pd.DataFrame(data = CHAINS_LIST, columns = ['chain_id', 'name'])
    chain_sel = st.selectbox(
        'Select chain:',
        chains_df,
        format_func = lambda x: chains_df[chains_df.chain_id == x]['name'].squeeze())
    if not chain_sel:
        st.error('Please select chain')
        st.stop()
    else:
        # tokens_df = get_tokens(chain_sel)
        tokens_df = pd.DataFrame(data = TOKENS_LIST, columns = ['address', 'symbol'])
        maker_asset = st.selectbox(
            'Select maker asset:',
            tokens_df,
            index = int(tokens_df[tokens_df.symbol == DEF_MAKER].index[0]),
            format_func = lambda x: tokens_df[tokens_df.address == x]['symbol'].squeeze()
        )
        taker_asset = st.selectbox(
            'Select taker asset:',
            tokens_df,
            index = int(tokens_df[tokens_df.symbol == DEF_TAKER].index[0]),
            format_func = lambda x: tokens_df[tokens_df.address == x]['symbol'].squeeze()
        )
        
if not maker_asset:
    st.error('Please select maker asset')
elif not taker_asset:
    st.error('Please select taker asset')
else:
    orders_df = get_limit_orders(chain_sel, maker_asset, taker_asset)
    st.title('Paraswap: Limit orders')
    if len(orders_df) > 0:
        orders_df['fillable_balance'] = orders_df['fillableBalance'].astype(float) / 1e18
        orders_df['maker_amount'] = orders_df['makerAmount'].astype(float) / 1e18
        orders_df['taker_amount'] = orders_df['takerAmount'].astype(float) / 1e18
        orders_df['rate'] = orders_df['taker_amount'] / orders_df['maker_amount']
        st.button('Refresh', on_click=click_refresh)
        
        col1, col2 = st.columns(2)
        total_fillable_balance = orders_df['fillable_balance'].sum()
        with col1:
            st.metric('Total fillable', f"{total_fillable_balance:,.0f}")
        with col2:
            weighted_rate = (orders_df['fillable_balance'] * orders_df['rate'] / total_fillable_balance).sum()
            st.metric('Weighted average rate', f"{weighted_rate:,.3f}")
        
        st.dataframe(
            orders_df[['fillable_balance', 'maker_amount', 'taker_amount', 'rate', 'maker']].sort_values('fillable_balance', ascending = False),
            hide_index = True      
        )

        fig, ax = plt.subplots()
        fig.set_figheight(2)
        ax.hist(x = orders_df['rate'], weights = orders_df['fillable_balance'], bins=20)
        st.pyplot(fig)
