# Treasury data
## Viewing Notebook
If you're using VSCode, its really as simple as installing the [Jupyter](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter) plugin after cloning this repo

## Queries
### UniV3
```yaml
{
  poolDayDatas(first: 7, orderBy: date, orderDirection: desc, where: {
    pool: "POOL_ADDRESS"
  }){
    date,
    sqrtPrice  # price = sqrtPrice^2 * 2^128
  }
}
```

### UniV2
```yaml
{
  pairDayDatas(first: 7, orderBy: date, orderDirection: desc, where: {
    pairAddress: "POOL_ADDRESS"
  }){
    date,
    reserve0,
    reserve1  # then the price against r1 is r0/r1
  }
}
```
