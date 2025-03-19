from bbgo import go
import debots

debots.set_api_keys()
price = go << "研究古罗马普通收入者的生活方式、收入和支出清单, 要具体的例子"

print(f"price=${price: .2f}")