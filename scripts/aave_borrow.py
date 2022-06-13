from scripts.helpful_scripts import get_account
from brownie import network, config, interface
from scripts.get_weth import get_weth
from web3 import Web3

# global amount
amount = Web3.toWei(0.1, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    # get_weth
    if network.show_active() in ["mainnet-fork-dev"]:
        get_weth()

    lending_pool = get_lending_pool()
    # Approve sending out ERC20 tokens

    approve_erc20(
        amount=amount,
        spender=lending_pool.address,
        erc20_address=erc20_address,
        account=account,
    )
    print("Depositing...")
    tx = lending_pool.deposit(
        erc20_address, amount, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Deposited")

    # .. how much to borrow and which token?
    borrowable_eth, total_debt = get_borrowable_data(lending_pool, account)
    print("Let's borrow!")
    # DAI in terms of ETH
    dai_to_eth = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )

    amount_of_dai_to_borrow = (1.0 / dai_to_eth) * borrowable_eth * 0.95
    # borrowable_eth -> borrowable_dai * 95%
    print(f"We are going to borrow {amount_of_dai_to_borrow} DAI")
    # now we will borrow
    dai_address = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_address,
        Web3.toWei(amount_of_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print("Borrowed some DAI!!")
    b_eth, total_debt = get_borrowable_data(lending_pool, account)
    print(b_eth)
    print(total_debt)

    repay_all(amount, lending_pool, account)
    print("You just deposited, borrowed, and repayed with Aave, Brownie and Chainlink")


def repay_all(amount, lending_pool, account):

    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        config["networks"][network.show_active()]["dai_token"],
        account,
    )
    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["dai_token"],
        amount,
        1,
        account.address,
        {"from": account},
    )
    repay_tx.wait(1)
    print("Repaid!")


def get_asset_price(price_feed_address):
    # ABI
    # Address
    dai_eth_price_feed = interface.AggregatorV3Interface(price_feed_address)
    lateset_price = dai_eth_price_feed.latestRoundData()[1]
    converted_price = Web3.fromWei(lateset_price, "ether")
    print(f"the dai eth price is {converted_price}")
    return float(converted_price)


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrow_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account)
    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")

    print(f"you have {total_collateral_eth} worth of ETH deposited.")
    print(f"You have {available_borrow_eth} worth of ETH to borrow")
    print(f"You have {total_debt_eth} worth of ETH debt")

    return (float(available_borrow_eth), float(total_debt_eth))


def approve_erc20(amount, spender, erc20_address, account):
    print("Approving ERC20 token...")
    # ABI
    # Address
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Approved!")
    return tx


def get_lending_pool():
    # ABI
    # Address
    lending_pool_address_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_address_provider.getLendingPool()
    # ABI
    # Address
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool
