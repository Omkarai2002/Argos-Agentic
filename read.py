with open("write.txt", "a+") as f:
    f.write("\n \n Hello again!")
    f.seek(0)          # go back to start
    print(f.read())