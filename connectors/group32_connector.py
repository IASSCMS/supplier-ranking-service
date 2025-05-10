"""
Integration connector with Group 32's Logistics & Route Optimization system.
This module handles data exchange between our Supplier Ranking system and
the Logistics & Route Optimization system using Google OR-Tools and Dijkstra's Algorithm.
"""

import json
import logging
import requests
import os
import random
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

class Group32Connector:
    """
    Connector class for integrating with Group 32's Logistics & Route Optimization system.
    Responsible for retrieving logistics data that affects supplier evaluations.
    """
    
    def __init__(self, base_url: str = "http://logistics-optimization-service:8000/api/v1/",
                 api_key: Optional[str] = None,
                 timeout: int = 10,
                 use_dummy_data=True):
        """
        Initialize the connector with configuration options.
        
        Args:
            base_url: Base URL for the logistics API
            api_key: API key for authentication if required
            timeout: Request timeout in seconds
            use_dummy_data: Flag to use dummy data for testing
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.headers["Content-Type"] = "application/json"
        
        # Flag to use dummy data for testing
        self.use_dummy_data = use_dummy_data
        
        logger.info(f"Initialized Group32Connector with base URL: {self.base_url}")
        
        # Generate dummy data for testing if needed
        if self.use_dummy_data:
            self._create_dummy_data()
    
    def _create_dummy_data(self):
        """Create dummy carbon footprint data for testing"""
        self.dummy_supplier_carbon = {}
        self.dummy_product_carbon = {}
        
        # Create dummy data for 20 suppliers
        for supplier_id in range(1, 21):
            # Use supplier_id as seed for consistent random data
            random.seed(supplier_id)
            
            # Generate carbon metrics with some variation
            carbon_score = round(random.uniform(3.0, 9.5), 1)
            if supplier_id % 4 == 0:  # Every 4th supplier has higher eco score
                carbon_score = min(carbon_score + 1.5, 10.0)
            
            emissions_tons = round(random.uniform(500, 10000), 0)
            if supplier_id % 3 == 0:  # Every 3rd supplier has lower emissions
                emissions_tons = round(emissions_tons * 0.7, 0)
            
            # Generate renewable energy percentage
            renewable_energy = round(random.uniform(10, 80), 1)
            if supplier_id % 5 == 0:  # Every 5th supplier has higher renewable energy
                renewable_energy = min(renewable_energy + 15, 100)
            
            # Store dummy data
            self.dummy_supplier_carbon[supplier_id] = {
                "supplier_id": supplier_id,
                "carbon_score": carbon_score,
                "total_emissions_tons": emissions_tons,
                "emissions_per_revenue": round(emissions_tons / (random.uniform(1, 10) * 1000000), 2),
                "renewable_energy_percentage": renewable_energy,
                "carbon_reduction_initiatives": random.randint(0, 5),
                "carbon_neutral_target_year": 2030 + random.randint(0, 10) if random.random() > 0.2 else None,
                "has_science_based_targets": random.random() > 0.6,
                "environmental_certifications": random.randint(0, 3),
                "last_updated": datetime.now().isoformat()
            }
        
        # Create dummy data for 100 products
        for product_id in range(1, 101):
            # Use product_id as seed for consistent random data
            random.seed(product_id)
            
            # Generate carbon metrics with variation
            carbon_per_unit = round(random.uniform(0.5, 100), 2)
            if product_id % 10 == 0:  # Every 10th product has lower carbon
                carbon_per_unit = round(carbon_per_unit * 0.5, 2)
            
            # Calculate carbon score - lower emissions = higher score
            carbon_score = round(10 - (carbon_per_unit / 20), 1)
            carbon_score = max(min(carbon_score, 10.0), 1.0)  # Clamp between 1 and 10
            
            # Store dummy data
            self.dummy_product_carbon[product_id] = {
                "product_id": product_id,
                "carbon_score": carbon_score,
                "carbon_per_unit_kg": carbon_per_unit,
                "manufacturing_emissions_pct": round(random.uniform(30, 70), 1),
                "materials_emissions_pct": round(random.uniform(10, 40), 1),
                "transport_emissions_pct": round(random.uniform(5, 20), 1),
                "has_eco_packaging": random.random() > 0.5,
                "recycled_materials_pct": round(random.uniform(0, 80), 1),
                "product_lifecycle_emissions_kg": round(carbon_per_unit * random.uniform(10, 20), 2),
                "last_updated": datetime.now().isoformat()
            }
    
    def get_supplier_logistics_score(self, supplier_id: int) -> Dict[str, Any]:
        """
        Retrieve logistics optimization score for a specific supplier.
        
        Args:
            supplier_id: ID of the supplier
            
        Returns:
            Dictionary containing logistics score and metrics
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"logistics/suppliers/{supplier_id}/score/"
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get supplier logistics score: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def get_route_efficiency(self, supplier_id: int, destination_id: int) -> Dict[str, Any]:
        """
        Get efficiency metrics for routes between a supplier and destination.
        
        Args:
            supplier_id: ID of the supplier
            destination_id: ID of the destination warehouse/facility
            
        Returns:
            Dictionary containing route efficiency metrics
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = "logistics/routes/efficiency/"
            params = {
                "supplier_id": supplier_id,
                "destination_id": destination_id
            }
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get route efficiency: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def get_transportation_costs(self, supplier_id: int, product_ids: List[int] = None) -> Dict[str, Any]:
        """
        Get transportation cost estimates for products from a supplier.
        
        Args:
            supplier_id: ID of the supplier
            product_ids: Optional list of product IDs to filter by
            
        Returns:
            Dictionary containing transportation cost data
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"logistics/suppliers/{supplier_id}/transportation-costs/"
            params = {}
            if product_ids:
                params["product_ids"] = ",".join(map(str, product_ids))
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get transportation costs: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def get_delivery_time_estimates(self, supplier_id: int, product_ids: List[int] = None) -> Dict[str, Any]:
        """
        Get estimated delivery times for products from a supplier.
        
        Args:
            supplier_id: ID of the supplier
            product_ids: Optional list of product IDs to filter by
            
        Returns:
            Dictionary containing delivery time estimates
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"logistics/suppliers/{supplier_id}/delivery-estimates/"
            params = {}
            if product_ids:
                params["product_ids"] = ",".join(map(str, product_ids))
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get delivery time estimates: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def get_logistics_disruptions(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get current logistics disruptions that might affect supplier performance.
        
        Args:
            region: Optional region code to filter disruptions
            
        Returns:
            List of disruption events
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = "logistics/disruptions/"
            params = {}
            if region:
                params["region"] = region
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get logistics disruptions: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def get_carbon_footprint(self, supplier_id: int) -> Dict[str, Any]:
        """
        Get carbon footprint metrics for a supplier's logistics operations.
        
        Args:
            supplier_id: ID of the supplier
            
        Returns:
            Dictionary containing carbon footprint data
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"logistics/suppliers/{supplier_id}/carbon-footprint/"
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get carbon footprint: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def optimize_supplier_selection(self, product_id: int, 
                                  quantity: int,
                                  delivery_location_id: int) -> Dict[str, Any]:
        """
        Get logistics-optimized supplier recommendations for a product order.
        
        Args:
            product_id: ID of the product
            quantity: Order quantity
            delivery_location_id: ID of the delivery location
            
        Returns:
            Dictionary containing optimized supplier recommendations
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = "logistics/optimize/supplier-selection/"
            data = {
                "product_id": product_id,
                "quantity": quantity,
                "delivery_location_id": delivery_location_id
            }
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to optimize supplier selection: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def get_warehouse_capacities(self) -> Dict[str, Any]:
        """
        Get current warehouse capacities to factor into supplier rankings.
        
        Returns:
            Dictionary containing warehouse capacity information
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = "logistics/warehouses/capacities/"
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get warehouse capacities: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")
    
    def update_supplier_logistics_profile(self, supplier_id: int, profile_data: Dict[str, Any]) -> bool:
        """
        Update logistics profile for a supplier based on ranking changes.
        
        Args:
            supplier_id: ID of the supplier
            profile_data: Updated logistics profile data
            
        Returns:
            True if update was successful
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"logistics/suppliers/{supplier_id}/profile/"
            
            response = requests.put(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=profile_data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to update supplier logistics profile: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        
        return False
    
    def get_route_analytics(self, supplier_id: int) -> Dict[str, Any]:
        """
        Get analytics about the supplier's logistics routes.
        
        Args:
            supplier_id: ID of the supplier
            
        Returns:
            Dictionary containing route analytics data
            
        Raises:
            ConnectionError: If unable to connect to the logistics service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"logistics/suppliers/{supplier_id}/route-analytics/"
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get route analytics: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 32's logistics service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from logistics service")
            raise ValueError("Invalid response from Group 32's logistics service")

    def get_supplier_carbon_metrics(self, supplier_id):
        """
        Get carbon footprint metrics for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Dictionary containing supplier carbon metrics
        """
        if self.use_dummy_data:
            # If we don't have dummy data for this supplier, generate it
            if supplier_id not in self.dummy_supplier_carbon:
                random.seed(supplier_id)
                
                carbon_score = round(random.uniform(3.0, 9.5), 1)
                emissions_tons = round(random.uniform(500, 10000), 0)
                renewable_energy = round(random.uniform(10, 80), 1)
                
                self.dummy_supplier_carbon[supplier_id] = {
                    "supplier_id": supplier_id,
                    "carbon_score": carbon_score,
                    "total_emissions_tons": emissions_tons,
                    "emissions_per_revenue": round(emissions_tons / (random.uniform(1, 10) * 1000000), 2),
                    "renewable_energy_percentage": renewable_energy,
                    "carbon_reduction_initiatives": random.randint(0, 5),
                    "carbon_neutral_target_year": 2030 + random.randint(0, 10) if random.random() > 0.2 else None,
                    "has_science_based_targets": random.random() > 0.6,
                    "environmental_certifications": random.randint(0, 3),
                    "last_updated": datetime.now().isoformat()
                }
            
            return self.dummy_supplier_carbon[supplier_id]
        
        try:
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/carbon",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching carbon metrics for supplier {supplier_id}: {str(e)}")
            # Return default data on error
            return {
                "supplier_id": supplier_id,
                "carbon_score": 6.5,
                "total_emissions_tons": 2500,
                "emissions_per_revenue": 0.25,
                "renewable_energy_percentage": 35.0,
                "error": "Failed to fetch real data"
            }
    
    def get_product_carbon_metrics(self, product_id):
        """
        Get carbon footprint metrics for a specific product
        
        Args:
            product_id (int): ID of the product
            
        Returns:
            dict: Dictionary containing product carbon metrics
        """
        if self.use_dummy_data:
            # If we don't have dummy data for this product, generate it
            if product_id not in self.dummy_product_carbon:
                random.seed(product_id)
                
                carbon_per_unit = round(random.uniform(0.5, 100), 2)
                carbon_score = round(10 - (carbon_per_unit / 20), 1)
                carbon_score = max(min(carbon_score, 10.0), 1.0)
                
                self.dummy_product_carbon[product_id] = {
                    "product_id": product_id,
                    "carbon_score": carbon_score,
                    "carbon_per_unit_kg": carbon_per_unit,
                    "manufacturing_emissions_pct": round(random.uniform(30, 70), 1),
                    "materials_emissions_pct": round(random.uniform(10, 40), 1),
                    "transport_emissions_pct": round(random.uniform(5, 20), 1),
                    "has_eco_packaging": random.random() > 0.5,
                    "recycled_materials_pct": round(random.uniform(0, 80), 1),
                    "product_lifecycle_emissions_kg": round(carbon_per_unit * random.uniform(10, 20), 2),
                    "last_updated": datetime.now().isoformat()
                }
            
            return self.dummy_product_carbon[product_id]
        
        try:
            response = requests.get(
                f"{self.base_url}/products/{product_id}/carbon",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching carbon metrics for product {product_id}: {str(e)}")
            # Return default data on error
            return {
                "product_id": product_id,
                "carbon_score": 6.0,
                "carbon_per_unit_kg": 25.0,
                "manufacturing_emissions_pct": 45.0,
                "materials_emissions_pct": 25.0,
                "transport_emissions_pct": 15.0,
                "error": "Failed to fetch real data"
            }
    
    def get_supplier_products_carbon(self, supplier_id):
        """
        Get carbon footprint metrics for all products from a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            list: List of product carbon metrics for the supplier
        """
        if self.use_dummy_data:
            # Generate dummy product carbon data for this supplier
            random.seed(supplier_id)
            num_products = random.randint(5, 15)
            
            products = []
            # Generate product IDs based on supplier ID for consistency
            product_ids = [supplier_id * 100 + i for i in range(1, num_products + 1)]
            
            for product_id in product_ids:
                product_data = self.get_product_carbon_metrics(product_id)
                product_data["supplier_id"] = supplier_id
                products.append(product_data)
            
            return products
        
        try:
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/products/carbon",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product carbon data for supplier {supplier_id}: {str(e)}")
            # Return empty list on error
            return []
    
    def get_supplier_carbon_history(self, supplier_id, months=12):
        """
        Get historical carbon emissions data for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            months (int): Number of months of historical data to retrieve
            
        Returns:
            list: List of historical carbon measurements
        """
        if self.use_dummy_data:
            # Generate dummy historical data
            random.seed(supplier_id)
            
            # Get current emissions as baseline
            current_data = self.get_supplier_carbon_metrics(supplier_id)
            current_emissions = current_data["total_emissions_tons"]
            
            # Generate trend factor - some suppliers improving, some getting worse
            trend_factor = random.uniform(0.85, 1.15)
            
            history = []
            today = datetime.now()
            
            for i in range(months):
                # Calculate date for this data point
                date = today - timedelta(days=30 * (months - i))
                
                # Calculate emissions with some trend and randomness
                month_emissions = current_emissions * (trend_factor ** ((months - i) / 12))
                month_emissions *= (1 + random.uniform(-0.05, 0.05))  # Add +/- 5% random noise
                
                history.append({
                    "date": date.strftime("%Y-%m"),
                    "emissions_tons": round(month_emissions, 0),
                    "renewable_percentage": round(
                        current_data["renewable_energy_percentage"] * 
                        (0.9 ** ((months - i) / 12)),  # Renewable % generally increasing over time
                        1
                    )
                })
            
            return history
        
        try:
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/carbon/history",
                headers=self.headers,
                params={"months": months},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching carbon history for supplier {supplier_id}: {str(e)}")
            # Return empty list on error
            return []
    
    def get_carbon_reduction_recommendations(self, supplier_id):
        """
        Get recommendations for carbon reduction for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            list: List of carbon reduction recommendations
        """
        if self.use_dummy_data:
            # Generate dummy recommendations
            random.seed(supplier_id)
            
            # Possible recommendations
            recommendations = [
                {
                    "id": 1,
                    "title": "Increase Renewable Energy Usage",
                    "description": "Switch to renewable energy sources for manufacturing facilities.",
                    "potential_reduction": f"{random.randint(10, 30)}%",
                    "implementation_cost": "High",
                    "timeframe": "1-3 years"
                },
                {
                    "id": 2,
                    "title": "Optimize Logistics Routes",
                    "description": "Reduce transportation emissions by optimizing shipping routes and consolidating shipments.",
                    "potential_reduction": f"{random.randint(5, 15)}%",
                    "implementation_cost": "Medium",
                    "timeframe": "6-12 months"
                },
                {
                    "id": 3,
                    "title": "Implement Energy Efficient Equipment",
                    "description": "Replace outdated manufacturing equipment with energy-efficient alternatives.",
                    "potential_reduction": f"{random.randint(8, 20)}%",
                    "implementation_cost": "High",
                    "timeframe": "1-2 years"
                },
                {
                    "id": 4,
                    "title": "Reduce Packaging Materials",
                    "description": "Redesign product packaging to use less material and more recyclable components.",
                    "potential_reduction": f"{random.randint(3, 10)}%",
                    "implementation_cost": "Low",
                    "timeframe": "3-6 months"
                },
                {
                    "id": 5,
                    "title": "Supplier Engagement Program",
                    "description": "Work with your suppliers to reduce upstream emissions in your supply chain.",
                    "potential_reduction": f"{random.randint(10, 25)}%",
                    "implementation_cost": "Medium",
                    "timeframe": "1-2 years"
                },
                {
                    "id": 6,
                    "title": "Carbon Offsetting Program",
                    "description": "Invest in certified carbon offset projects to compensate for emissions.",
                    "potential_reduction": "Variable",
                    "implementation_cost": "Medium",
                    "timeframe": "3-6 months"
                },
                {
                    "id": 7,
                    "title": "Material Substitution",
                    "description": "Replace carbon-intensive materials with lower-carbon alternatives.",
                    "potential_reduction": f"{random.randint(5, 20)}%",
                    "implementation_cost": "Medium to High",
                    "timeframe": "6-18 months"
                }
            ]
            
            # Select a random number of recommendations
            num_recommendations = random.randint(2, 5)
            return random.sample(recommendations, num_recommendations)
        
        try:
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/carbon/recommendations",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching carbon recommendations for supplier {supplier_id}: {str(e)}")
            # Return empty list on error
            return []
    
    def test_connection(self):
        """
        Test connection to the Carbon Footprint Service
        Returns True if connection is successful, False otherwise
        """
        if self.use_dummy_data:
            # Always return success when using dummy data
            return True
            
        try:
            # Try to connect to the base URL with auth headers for auth-required endpoints
            response = requests.get(
                f"{self.base_url}/health-check",
                headers=self.headers,
                timeout=5  # Short timeout for health check
            )
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False