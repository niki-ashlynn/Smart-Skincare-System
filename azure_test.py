from azure_connection import connect_azure, disconnect_azure


# azure connection test ---------------------------------------------

print("starting azure connection...")

if connect_azure():
    print("azure is working!")
else:
    print("azure is not connected")

disconnect_azure()

