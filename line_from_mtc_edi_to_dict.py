def capture_records(line):
    if line.startswith("A"):
        fields = dict(record_type=line[0],
                      cust_vendor=line[1:7],
                      invoice_number=line[7:17],
                      invoice_date=line[17:23],
                      invoice_total=line[23:33])
        return fields
    elif line.startswith("B"):
        fields = dict(record_type=line[0],
                      upc_number=line[1:12],
                      description=line[12:37],
                      vendor_item=line[37:43],
                      unit_cost=line[43:49],
                      combo_code=line[49:51],
                      unit_multiplier=line[51:57],
                      qty_of_units=line[57:62],
                      suggested_retail_price=line[62:67],
                      price_multi_pack = line[67:70],
                      parent_item_number = line[70:76])
        return fields
    elif line.startswith("C"):
        fields = dict(record_type=line[0],
                      charge_type=line[1:4],
                      description=line[4:29],
                      amount=line[29:38])
        return fields
    elif line.startswith(""):
        return None
    else:
        raise Exception("Not An EDI")
