def capture_records(line):
    if line.startswith("B"):
        fields = dict(record_type=line[0],
                      upc_number=line[1:12],
                      description=line[12:37],
                      vendor_item=line[37:43],
                      unit_cost=line[43:49],
                      combo_code=line[49:51],
                      unit_multiplier=line[51:57],
                      qty_of_units=line[57:62],
                      suggested_retail_price=line[62:67])
        return fields
    else:
        raise Exception("Not An EDI")
