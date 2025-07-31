import streamlit as st
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from langchain_ollama import OllamaLLM
from langchain.agents import Tool, initialize_agent, AgentType
import pandas as pd

# Configuration

st.set_page_config(
    page_title="Ecommerce AI Agents Sandbox By Ronnie",
    page_icon="🛒",
    layout="wide"
)

# Data Models
@dataclass
class Product:
    id: str
    name: str
    category: str
    price: float
    description: str
    stock: int
    rating: float
    tags: List[str]

@dataclass
class CartItem:
    product_id: str
    quantity: int
    added_at: str

@dataclass
class User:
    id: str
    name: str
    cart: List[CartItem]
    wishlist: List[str]
    purchase_history: List[Dict]


# Database setup
class EcommerceDB:
    
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.set_database()
        self.populate_sample_data()

    def set_database(self):
        cursor = self.conn.cursor()

        # Products table

        cursor.execute('''
                    CREATE TABLE products (
                       id TEXT PRIMARY KEY,
                       name TEXT NOT NULL,
                       category TEXT NOT NULL,
                       price REAL NOT NULL,
                       description TEXT,
                       stock INTEGER NOT NULL,
                       rating REAL,
                       tags TEXT
                       )
                ''')
        
        # Users table

        cursor.execute('''
            CREATE TABLE users (
                       id TEXT PRIMARY KEY,
                       name TEXT NOT NULL,
                       cart TEXT,
                       wishlist TEXT,
                       purchase_history TEXT
                       )
        ''')

        self.conn.commit()

    def populate_sample_data(self):
        sample_products = [
            Product("1", "iPhone 15 Pro", "Electronics", 999.99, "Latest iPhone with A17 Pro chip", 50, 4.8, ["smartphone", "apple", "premium"]),
            Product("2", "Samsung Galaxy S24", "Electronics", 799.99, "Android flagship with AI features", 30, 4.7, ["smartphone", "samsung", "android"]),
            Product("3", "MacBook Air M3", "Electronics", 1299.99, "Lightweight laptop with M3 chip", 25, 4.9, ["laptop", "apple", "m3"]),
            Product("4", "Nike Air Max 270", "Fashion", 150.00, "Comfortable running shoes", 100, 4.5, ["shoes", "nike", "running"]),
            Product("5", "Levi's 501 Jeans", "Fashion", 89.99, "Classic straight-fit jeans", 75, 4.4, ["jeans", "levis", "denim"]),
            Product("6", "The Great Gatsby", "Books", 12.99, "Classic American novel", 200, 4.6, ["book", "classic", "fiction"]),
            Product("7", "Instant Pot Duo 7-in-1", "Home & Kitchen", 79.99, "Multi-use pressure cooker", 40, 4.7, ["kitchen", "cooking", "appliance"]),
            Product("8", "Dyson V15 Detect", "Home & Kitchen", 749.99, "Cordless vacuum with laser detection", 15, 4.8, ["vacuum", "dyson", "cordless"]),
            Product("9", "PlayStation 5", "Electronics", 499.99, "Next-gen gaming console", 20, 4.9, ["gaming", "playstation", "console"]),
            Product("10", "AirPods Pro 2", "Electronics", 249.99, "Noise-cancelling wireless earbuds", 60, 4.6, ["earbuds", "apple", "wireless"])
        ]

        cursor = self.conn.cursor()

        for product in sample_products:
            cursor.execute(
                '''
                    INSERT INTO products VALUES (?,?,?,?,?, ?, ?, ?)
                ''', (product.id, product.name, product.category, product.price, product.description, product.stock, product.rating, json.dumps(product.tags))
            )

        # sample user
        sample_user = User("user1", "Ronnie Kakunguwo", [], [], [])
        cursor.execute(
            '''INSERT INTO users VALUES(?,?,?,?,?)''',
            (sample_user.id, sample_user.name, json.dumps([]), json.dumps([]), json.dumps([]))
        )

        self.conn.commit()

    def search_products(self, query: str, category: str = None) -> List[Dict]:
        cursor = self.conn.cursor()

        if category:
            cursor.execute(
                '''
                    SELECT * FROM products
                    WHERE (name LIKE ? OR description LIKE ? OR tags LIKE ?)
                    AND category = ?
                    ORDER BY rating DESC
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', category)
            )
        else:
            cursor.execute(
                '''
                    SELECT * FROM products
                    WHERE name LIKE ? OR description LIKE ? OR tags LIKE ?
                    ORDER BY rating DESC
                ''', (f'%{query}%', f'%{query}%', f'%{query}%')
            )
        
        results = cursor.fetchall()

        return [
            {'id': r[0], 'name': r[1], 'category': r[2], 'price': r[3], 'description': r[4], 'stock': r[5], 'rating': r[6], 'tags': json.loads(r[7])} for r in results
        ]
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        result = cursor.fetchone()
        if result:
            return {'id': result[0], 'name': result[1], 'category': result[2], 
                   'price': result[3], 'description': result[4], 'stock': result[5], 
                   'rating': result[6], 'tags': json.loads(result[7])}
        return None
    
    def get_user_cart(self, user_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT cart FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            cart_items = json.loads(result[0])
            detailed_cart = []
            for item in cart_items:
                product = self.get_product(item['product_id'])
                if product:
                    detailed_cart.append({
                        'product': product,
                        'quantity': item['quantity'],
                        'added_at': item['added_at']
                    })
            return detailed_cart
        return []
    
    def get_user_wishlist(self, user_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT wishlist FROM users WHERE id = ?', (user_id))
        result = cursor.fetchone()
        if result:
            wishlist_items = json.loads(result[0])
            detailed_wishlist = []
            for item in wishlist_items:
                product = self.get_product(item['product_id'])
                if product:
                    detailed_wishlist.append({
                        'product': product
                    })
            return detailed_wishlist
        return []
    

    def add_to_cart(self, user_id: str, product_id: str, quantity: int = 1):
        cursor = self.conn.cursor()
        cursor.execute('SELECT cart FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            cart = json.loads(result[0])
            # Check if product already in cart
            for item in cart:
                if item['product_id'] == product_id:
                    item['quantity'] += quantity
                    break
            else:
                cart.append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'added_at': datetime.now().isoformat()
                })
            
            cursor.execute('UPDATE users SET cart = ? WHERE id = ?', 
                         (json.dumps(cart), user_id))
            self.conn.commit()
            return True
        return False
    

    def add_to_wishlist(self, user_id: str, product_id: str):
        cursor = self.conn.cursor()
        cursor.execute('SELECT wishlist FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            wishlist = json.loads(result[0])
            if product_id not in wishlist:
                wishlist.append(product_id)
                cursor.execute('UPDATE users SET wishlist = ? WHERE id = ?', 
                             (json.dumps(wishlist), user_id))
                self.conn.commit()
            return True
        return False
    

    def get_categories(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM products')
        return [row[0] for row in cursor.fetchall()]
    

# Initialize database
if 'db' not in st.session_state:
    st.session_state.db = EcommerceDB()


# AI Agent Tools
class EcommerceTools:
    def __init__(self, db: EcommerceDB):
        self.db = db

    def search_products_tool(self, query: str) -> str:
        """Search for products based on query"""
        # Try both with and without category filter
        results = self.db.search_products(query)
        
       
        if not results and query.lower() in ['smartphone', 'smartphones', 'phone', 'phones']:
            results = self.db.search_products("", "Electronics")
            # Filter for phone-related products
            results = [p for p in results if any(tag in ['smartphone', 'apple', 'samsung', 'phone'] for tag in p['tags'])]
        
        if not results:
            return f"No products found for '{query}'. Try searching for 'phone', 'laptop', 'shoes', or browse by category."
        
        formatted_results = []
        for product in results[:5]:  # Limit to top 5 results
            formatted_results.append(
                f"ID: {product['id']}, Name: {product['name']}, "
                f"Price: ${product['price']:.2f}, Rating: {product['rating']}/5, "
                f"Stock: {product['stock']}"
            )
        
        # Add helpful instructions at the end
        response = "Found products:\n" + "\n".join(formatted_results)
        response += "\n\nTo add any product to cart, say 'add product ID X to cart' where X is the product ID."
        response += "\nFor more details about a product, say 'show details for product ID X'."
        
        return response
    
    def add_to_cart_tool(self, product_id: str, quantity: str = "1") -> str:
        """Add a product to the user's cart"""
        try:
            qty = int(quantity)
            product = self.db.get_product(product_id)
            if not product:
                return f"Product with ID {product_id} not found"
            
            if product['stock'] < qty:
                return f"Sorry, only {product['stock']} items available for {product['name']}"
            
            success = self.db.add_to_cart("user1", product_id, qty)
            if success:
                return f"Added {qty} x {product['name']} to cart successfully!"
            else:
                return "Failed to add item to cart"
        except ValueError:
            return "Invalid quantity specified"
        

    def add_to_wishlist_tool(self, product_id: str) -> str:
        """Add a product to the user's wishlist"""
        product = self.db.get_product(product_id)
        if not product:
            return f"Product with ID {product_id} not found"
        
        success = self.db.add_to_wishlist("user1", product_id)
        if success:
            return f"Added {product['name']} to wishlist!"
        else:
            return "Failed to add item to wishlist"
        
    
    def get_cart_tool(self, dummy: str = "") -> str:
        """Get the current cart contents"""
        cart = self.db.get_user_cart("user1")
        if not cart:
            return "Your cart is empty"
        
        cart_info = ["Current cart contents:"]
        total = 0
        for item in cart:
            subtotal = item['product']['price'] * item['quantity']
            total += subtotal
            cart_info.append(
                f"- {item['product']['name']} x{item['quantity']} = ${subtotal:.2f}"
            )
        cart_info.append(f"Total: ${total:.2f}")
        return "\n".join(cart_info)
    

    def get_product_details_tool(self, product_id: str) -> str:
        """Get detailed information about a specific product"""
        product = self.db.get_product(product_id)
        if not product:
            return f"Product with ID {product_id} not found"
        
        return (f"Product Details:\n"
                f"Name: {product['name']}\n"
                f"Category: {product['category']}\n"
                f"Price: ${product['price']:.2f}\n"
                f"Description: {product['description']}\n"
                f"Rating: {product['rating']}/5\n"
                f"Stock: {product['stock']} available\n"
                f"Tags: {', '.join(product['tags'])}")
    

# Initialise Ollama LLM
@st.cache_resource
def initialize_llm():
    return OllamaLLM(model="gemma3:1b")


# Initialise AI Agent
def get_agent():
    if 'agent' not in st.session_state:
        llm = initialize_llm()
        tools_handler = EcommerceTools(st.session_state.db)
        
        tools = [
            Tool(
                name="SearchProducts",
                func=tools_handler.search_products_tool,
                description="Search for products by name, description, or tags. Input should be a search query string. Use this to find products for the user."
            ),
            Tool(
                name="AddToCart",
                func=tools_handler.add_to_cart_tool,
                description="Add a product to cart. Input should be 'product_id,quantity' or just 'product_id' for quantity 1."
            ),
            Tool(
                name="AddToWishlist",
                func=tools_handler.add_to_wishlist_tool,
                description="Add a product to wishlist. Input should be the product_id."
            ),
            Tool(
                name="GetCart",
                func=tools_handler.get_cart_tool,
                description="Get current cart contents and total. No input needed, just use empty string."
            ),
            Tool(
                name="GetProductDetails",
                func=tools_handler.get_product_details_tool,
                description="Get detailed information about a specific product. Input should be the product_id."
            )
        ]
        
        from langchain.memory import ConversationBufferMemory
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        st.session_state.agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  
            memory=memory,
            verbose=True,
            max_iterations=2,  
            handle_parsing_errors=True,
            early_stopping_method="generate"  
        )
    
    return st.session_state.agent


def get_simple_agent():
    if 'simple_agent' not in st.session_state:
        llm = initialize_llm()
        tools_handler = EcommerceTools(st.session_state.db)
        
        tools = [
            Tool(
                name="SearchProducts",
                func=tools_handler.search_products_tool,
                description="Search for products. Input: search query as string"
            ),
            Tool(
                name="AddToCart",
                func=tools_handler.add_to_cart_tool,
                description="Add product to cart. Input: product_id"
            ),
            Tool(
                name="GetCart",
                func=tools_handler.get_cart_tool,
                description="Show cart contents. Input: empty string"
            ),
            Tool(
                name="GetProductDetails",
                func=tools_handler.get_product_details_tool,
                description="Get product details. Input: product_id"
            )
        ]
        
        
        st.session_state.simple_agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,  
            max_iterations=1, 
            handle_parsing_errors=True
        )
    
    return st.session_state.simple_agent


# Streamlit UI
def main():
    st.title("E-commerce AI Agents Sandbox by Ronnie")
    st.sidebar.title("Navigation")
    
    # Sidebar options
    page = st.sidebar.selectbox("Choose a page", [
        "AI Chat Interface",
        "Product Database",
        "Cart & Wishlist",
        "Agent Testing",
        "System Logs"
    ])
    
    if page == "AI Chat Interface":
        ai_chat_interface()
    elif page == "Product Database":
        product_database_view()
    elif page == "Cart & Wishlist":
        cart_wishlist_view()
    elif page == "Agent Testing":
        agent_testing_interface()
    elif page == "System Logs":
        system_logs_view()


def ai_chat_interface():
    st.header("AI Shopping Assistant")
    st.write("Chat with the AI agent using natural language!")
    
    # Add Ollama status check
    col1, col2 = st.columns([3, 1])
    with col2:
        ollama_status = check_ollama_status()
        if ollama_status:
            st.success("🟢 AI Online")
        else:
            st.warning("🟡 Pattern Mode")
    
    # Initialise chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # clear chat button
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        if 'ai_agent' in st.session_state:
            del st.session_state.ai_agent  # Reset agent
        st.rerun()
    
    # Show example prompts
    st.sidebar.subheader("Try these examples:")
    example_prompts = [
        "Hi there!",
        "I'm looking for a laptop",
        "Show me some smartphones", 
        "Add the MacBook to my cart",
        "What's in my cart?",
    ]
    
    for prompt in example_prompts:
        if st.sidebar.button(prompt, key=f"example_{prompt}"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            try:
                with st.spinner("AI is thinking..."):
                    if ollama_status:
                        response = handle_user_query_with_ai(prompt)
                    else:
                        response = handle_user_query(prompt)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {str(e)}")
    
    # Chat input
    user_input = st.chat_input("Type your message naturally...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get AI response
        try:
            with st.spinner("AI is thinking..."):
                if ollama_status:
                    response = handle_user_query_with_ai(user_input)
                else:
                    response = handle_user_query(user_input)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": f"I encountered an issue: {str(e)}. Please try rephrasing your request."
            })
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

def check_ollama_status():
    """Check if Ollama is running and responsive"""
    try:
        llm = initialize_llm()
        test_response = llm.invoke("Hi")
        return bool(test_response and len(test_response.strip()) > 0)
    except Exception:
        return False

def product_database_view():
    st.header("Product Database")
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search products...")
    with col2:
        category = st.selectbox("Category", ["All"] + st.session_state.db.get_categories())
    
    # Display products
    if search_query:
        cat_filter = None if category == "All" else category
        products = st.session_state.db.search_products(search_query, cat_filter)
    else:
        # Show all products
        products = st.session_state.db.search_products("", None)
    
    if products:
        for product in products:
            with st.expander(f"{product['name']} - ${product['price']:.2f}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Category:** {product['category']}")
                    st.write(f"**Description:** {product['description']}")
                    st.write(f"**Rating:** {product['rating']}/5 ⭐")
                    st.write(f"**Stock:** {product['stock']} available")
                    st.write(f"**Tags:** {', '.join(product['tags'])}")
                with col2:
                    if st.button(f"Add to Cart", key=f"cart_{product['id']}"):
                        st.session_state.db.add_to_cart("user1", product['id'])
                        st.success("Added to cart!")
                    if st.button(f"Add to Wishlist", key=f"wish_{product['id']}"):
                        st.session_state.db.add_to_wishlist("user1", product['id'])
                        st.success("Added to wishlist!")


def cart_wishlist_view():
    st.header("Cart & Wishlist")
    
    tab1, tab2 = st.tabs(["Shopping Cart", "Wishlist"])
    
    with tab1:
        st.subheader("Shopping Cart")
        cart = st.session_state.db.get_user_cart("user1")
        
        if cart:
            total = 0
            for item in cart:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{item['product']['name']}**")
                    st.write(f"${item['product']['price']:.2f} each")
                with col2:
                    st.write(f"Qty: {item['quantity']}")
                with col3:
                    subtotal = item['product']['price'] * item['quantity']
                    st.write(f"${subtotal:.2f}")
                    total += subtotal
                st.divider()
            
            st.subheader(f"Total: ${total:.2f}")
        else:
            st.info("Your cart is empty")
    
    with tab2:
        st.subheader("Wishlist")
        st.info("Wishlist functionality will show saved items here")


def agent_testing_interface():
    st.header("AI Agent Testing Interface")
    
    st.write("Test the AI agent with natural language queries")
    
    # Check Ollama status
    ollama_status = check_ollama_status()
    if ollama_status:
        st.success("🟢 Ollama AI is running")
    else:
        st.warning("🟡 Ollama not available - using pattern matching fallback")
    
    # Test scenarios with natural language
    test_scenarios = [
        "Hello, how are you?",
        "I need a new laptop for work",
        "Show me the best smartphones you have", 
        "Can you add that MacBook to my shopping cart?",
        "What do I have in my cart right now?",
        "Tell me more details about the iPhone",
        "I'm looking for running shoes",
        "Add product number 1 to my cart please"
    ]
    
    st.subheader("Natural Language Test Scenarios")
    for scenario in test_scenarios:
        if st.button(scenario, key=f"test_{scenario}"):
            try:
                with st.spinner("AI Processing..."):
                    if ollama_status:
                        response = handle_user_query_with_ai(scenario)
                    else:
                        response = handle_user_query(scenario)
                st.success("AI Response:")
                st.write(response)
                st.divider()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Custom test input
    st.subheader("Custom Natural Language Test")
    custom_test = st.text_area("Enter any natural language request:")
    if st.button("Test with AI") and custom_test:
        try:
            with st.spinner("AI Processing..."):
                if ollama_status:
                    response = handle_user_query_with_ai(custom_test)
                else:
                    response = handle_user_query(custom_test)
            st.success("AI Response:")
            st.write(response)
        except Exception as e:
            st.error(f"Error: {str(e)}")


def system_logs_view():
    st.header("System Logs & Analytics")
    
    # Database stats
    st.subheader("Database Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_products = len(st.session_state.db.search_products("", None))
        st.metric("Total Products", total_products)
    
    with col2:
        categories = st.session_state.db.get_categories()
        st.metric("Categories", len(categories))
    
    with col3:
        cart_items = st.session_state.db.get_user_cart("user1")
        st.metric("Cart Items", len(cart_items))
    
    # Agent interaction logs
    st.subheader("Recent Interactions")
    if 'chat_history' in st.session_state:
        df = pd.DataFrame(st.session_state.chat_history)
        if not df.empty:
            st.dataframe(df)
    else:
        st.info("No interactions logged yet")

def handle_user_query(user_input: str) -> str:
    """Handle user queries directly without complex agent"""
    user_input_lower = user_input.lower()
    tools_handler = EcommerceTools(st.session_state.db)
    
    # Greetings
    if any(greeting in user_input_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
        return "Hello! Welcome to our AI Shopping Assistant! 🛒\n\nI can help you:\n- Search for products\n- Add items to your cart\n- View your cart\n- Get product details\n\nWhat would you like to find today?"
    
    # Positive responses
    if any(phrase in user_input_lower for phrase in ['doing great', 'good', 'fine', 'excellent']):
        return "That's wonderful to hear! How can I help you with your shopping today? You can ask me to find products, check your cart, or get details about any item."
    
    # MacBook/laptop searches
    if any(term in user_input_lower for term in ['macbook', 'laptop', 'mac book']):
        result = tools_handler.search_products_tool("macbook")
        return f"Here are the MacBook laptops I found:\n\n{result}"
    
    # Electronics searches
    if 'electronics' in user_input_lower or 'gadget' in user_input_lower:
        result = tools_handler.search_products_tool("electronics")
        return f"Here are some electronics I found:\n\n{result}"
    
    # Phone/smartphone searches
    if any(term in user_input_lower for term in ['phone', 'smartphone', 'iphone', 'samsung']):
        result = tools_handler.search_products_tool("phone")
        return f"Here are the phones I found:\n\n{result}"
    
    # Cart operations
    if 'cart' in user_input_lower and any(word in user_input_lower for word in ['show', 'view', 'my', 'check']):
        return tools_handler.get_cart_tool("")
    
    # Add to cart (extract product ID)
    if 'add' in user_input_lower and 'cart' in user_input_lower:
        # Try to extract product ID
        import re
        id_match = re.search(r'(?:id|product)\s*(\d+)', user_input_lower)
        if id_match:
            product_id = id_match.group(1)
            return tools_handler.add_to_cart_tool(product_id)
        else:
            return "Please specify the product ID you want to add to cart. For example: 'add product ID 3 to cart'"
    
    # Product details
    if 'details' in user_input_lower or 'info' in user_input_lower:
        import re
        id_match = re.search(r'(?:id|product)\s*(\d+)', user_input_lower)
        if id_match:
            product_id = id_match.group(1)
            return tools_handler.get_product_details_tool(product_id)
        else:
            return "Please specify the product ID you want details for. For example: 'show details for product ID 3'"
    
    # General search
    # Extract search terms (remove common words)
    search_terms = user_input_lower
    for word in ['search', 'find', 'looking', 'for', 'show', 'me', 'i', 'need', 'want', 'help', 'with']:
        search_terms = search_terms.replace(word, '')
    search_terms = search_terms.strip()
    
    if search_terms:
        result = tools_handler.search_products_tool(search_terms)
        return f"Here's what I found for '{search_terms}':\n\n{result}"
    
    # Default response
    return "I'd be happy to help you find products! You can ask me to:\n- Search for specific items (e.g., 'find smartphones')\n- Show your cart\n- Add items to cart using product ID\n- Get product details\n\nWhat would you like to do?"

def create_ai_agent():
    """Create a simple but effective AI agent using Ollama"""
    if 'ai_agent' not in st.session_state:
        llm = initialize_llm()
        tools_handler = EcommerceTools(st.session_state.db)
        
        # Create a simple prompt template for the AI
        prompt_template = """
You are a helpful e-commerce shopping assistant. You can help users:
1. Search for products
2. Add items to cart
3. View cart contents
4. Get product details

Available tools and their exact usage:
- search_products(query): Search for products by name/description
- add_to_cart(product_id): Add a product to cart by ID
- get_cart(): Show current cart contents
- get_product_details(product_id): Get detailed info about a product

User message: {user_input}

Based on the user's message, determine what they want to do and respond naturally. If you need to use a tool, explain what you're doing and then provide the results in a conversational way.

Response:"""

        st.session_state.ai_agent = {
            'llm': llm,
            'tools': tools_handler,
            'prompt': prompt_template
        }
    
    return st.session_state.ai_agent

def handle_user_query_with_ai(user_input: str) -> str:
    """Handle user queries using actual AI with natural language understanding"""
    try:
        # First, check if Ollama is working
        agent = create_ai_agent()
        llm = agent['llm']
        tools = agent['tools']
        
        # Test Ollama connection first
        test_response = llm.invoke("Hello")
        if not test_response:
            # Fallback to pattern matching if Ollama is not responding
            return handle_user_query(user_input)
        
        # First, let the AI understand what the user wants
        understanding_prompt = f"""
Analyze this user message and determine their intent: "{user_input}"

What does the user want to do? Reply with just one of these actions:
- SEARCH: if they want to find/search for products
- ADD_TO_CART: if they want to add something to cart
- VIEW_CART: if they want to see their cart
- PRODUCT_DETAILS: if they want details about a specific product
- GREETING: if they're greeting or being friendly
- OTHER: if it's something else

Intent:"""
        
        intent_response = llm.invoke(understanding_prompt)
        intent = intent_response.strip().upper()
        
        # Based on intent, extract relevant information and take action
        if "SEARCH" in intent:
            # Extract what they're searching for
            search_prompt = f"""
Extract the search terms from this message: "{user_input}"
What product or category are they looking for? Reply with just the search terms.
Examples:
- "I need a macbook" -> "macbook"
- "find smartphones" -> "smartphones"  
- "looking for running shoes" -> "running shoes"

Search terms:"""
            
            search_terms = llm.invoke(search_prompt).strip()
            results = tools.search_products_tool(search_terms)
            
            # Generate natural response
            response_prompt = f"""
The user searched for "{search_terms}" and here are the results:
{results}

Write a natural, helpful response to the user about these search results. Be conversational and friendly.

Response:"""
            
            return llm.invoke(response_prompt)
            
        elif "ADD_TO_CART" in intent:
            # Extract product information
            extract_prompt = f"""
The user wants to add something to cart: "{user_input}"
Extract the product ID if mentioned, or the product name they want to add.
If they mentioned a specific product from a previous search, try to identify it.

Examples:
- "add product ID 3 to cart" -> "3"
- "add this macbook to cart" -> "macbook"
- "add the iPhone to my cart" -> "iPhone"

Product identifier:"""
            
            product_info = llm.invoke(extract_prompt).strip()
            
            # Try to add to cart
            if product_info.isdigit():
                # It's a product ID
                result = tools.add_to_cart_tool(product_info)
            else:
                # It's a product name, need to search first
                search_results = tools.search_products_tool(product_info)
                if "Found products:" in search_results:
                    # Extract first product ID from search results
                    import re
                    id_match = re.search(r'ID: (\d+)', search_results)
                    if id_match:
                        product_id = id_match.group(1)
                        result = tools.add_to_cart_tool(product_id)
                    else:
                        result = f"I found some products for '{product_info}' but couldn't determine which one you want. Please specify the product ID."
                else:
                    result = f"Sorry, I couldn't find any products matching '{product_info}'"
            
            # Generate natural response
            response_prompt = f"""
The user tried to add something to cart and here's what happened:
{result}

Write a natural, conversational response about this cart operation.

Response:"""
            
            return llm.invoke(response_prompt)
            
        elif "VIEW_CART" in intent:
            cart_contents = tools.get_cart_tool("")
            
            response_prompt = f"""
The user wants to see their cart. Here's what's in it:
{cart_contents}

Write a natural, friendly response showing their cart contents.

Response:"""
            
            return llm.invoke(response_prompt)
            
        elif "PRODUCT_DETAILS" in intent:
            # Extract product ID or name
            extract_prompt = f"""
Extract the product identifier from: "{user_input}"
Look for product ID numbers or product names they want details about.

Product identifier:"""
            
            product_info = llm.invoke(extract_prompt).strip()
            
            if product_info.isdigit():
                result = tools.get_product_details_tool(product_info)
            else:
                result = "Please specify the product ID you want details for."
            
            response_prompt = f"""
The user requested product details and here's the information:
{result}

Write a natural, helpful response presenting this product information.

Response:"""
            
            return llm.invoke(response_prompt)
            
        elif "GREETING" in intent:
            greeting_prompt = f"""
The user said: "{user_input}"
Write a warm, friendly greeting response as an e-commerce shopping assistant. 
Briefly mention what you can help with.

Response:"""
            
            return llm.invoke(greeting_prompt)
            
        else:
            # Handle other cases
            general_prompt = f"""
The user said: "{user_input}"
As an e-commerce shopping assistant, provide a helpful response. If you're not sure what they want, 
ask for clarification and mention what you can help with.

Response:"""
            
            return llm.invoke(general_prompt)
            
    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        # Fallback to pattern matching if AI fails
        return handle_user_query(user_input)
    

if __name__ == "__main__":
    main()