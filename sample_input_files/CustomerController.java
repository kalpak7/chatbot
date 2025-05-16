package com.Controller;

import com.DAO.CustomerDAO;
import com.Model.Consumer;
import com.Model.Customer;


import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

public class CustomerController {

    public int registerCustomer(Customer customer,Consumer consumer) {
      CustomerDAO temp = new CustomerDAO();
      try {
		return temp.register(customer, consumer);
	} catch (SQLException e) {
		// TODO Auto-generated catch block
		e.printStackTrace();
	}
	return 0;
    }
    public long getConsumerNumber(String id) {
        CustomerDAO temp = new CustomerDAO();
        try {
  		return temp.getConsumerNumber(id);
  	} catch (SQLException e) {
  		// TODO Auto-generated catch block
  		e.printStackTrace();
  		return 0;
  	}
  	
      }

//    public ArrayList fetchCustomer(String customerId) {
//      CustomerDAO temp = new CustomerDAO();
//      try {
//		return temp.getCustomerById(customerId);
//	} catch (SQLException e) {
//		// TODO Auto-generated catch block
//		e.printStackTrace();
//	}
//	return null;
//    }
//
    public ArrayList<Customer> fetchAllCustomers() {
      CustomerDAO temp = new CustomerDAO();
      try {
		return temp.getCustomers();
	} catch (SQLException e) {
		// TODO Auto-generated catch block
		e.printStackTrace();
	}
	return null;
    }
//
//    public int updateCustomer(Customer customer) {
//      CustomerDAO temp = new CustomerDAO();
//      return temp.updateCustomer(customer);
//    }
//
//    public int deleteCustomer(String customerId) {
//      CustomerDAO temp = new CustomerDAO();
//      return temp.deleteCustomer(customerId);
//    }
}
