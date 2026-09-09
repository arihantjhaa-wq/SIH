// Commodity data loader for Market Insights
// This loads the JSON file and extracts all unique commodity names
getCommodities: () => {
  // Read the JSON file
  const fs = require('fs');
  const path = require('path');

  try {
    const jsonPath = path.join(__dirname, 'price-forecaster-service', 'india_agricultural_prices_last_5_days_june_september_2026.json');
    const jsonContent = fs.readFileSync(jsonPath, 'utf8');
    const data = JSON.parse(jsonContent);

    // Extract all unique commodity names from the JSON
    // The JSON has a structure with "commodities" array containing objects with "commodity_name"
    const allCommodities = [];

    // Get commodities from the main commodities array
    if (data.commodities && Array.isArray(data.commodities)) {
      data.commodities.forEach(item => {
        if (item.commodity_name && !allCommodities.includes(item.commodity_name)) {
          allCommodities.push(item.commodity_name);
        }
      });
    }

    // Also check if there are other commodity arrays in the JSON
    // This handles cases where commodities might be in different sections
    const possibleCommodityKeys = ['commodities', 'crops', 'vegetables', 'fruits', 'items'];
    possibleCommodityKeys.forEach(key => {
      if (data[key] && Array.isArray(data[key])) {
        data[key].forEach(item => {
          const name = item.commodity_name || item.name || item.item;
          if (name && !allCommodities.includes(name)) {
            allCommodities.push(name);
          }
        });
      }
    });

    // Sort alphabetically for better UX
    return allCommodities.sort();

  } catch (error) {
    console.error('Error loading commodity data:', error);
    // Fallback to basic list if JSON fails to load
    return [
      "Rice", "Wheat", "Maize", "Barley", "Sorghum", "Millets", "Oats",
      "Tomato", "Onion", "Potato", "Carrot", "Cabbage", "Cauliflower", "Broccoli", "Spinach",
      "Apple", "Banana", "Orange", "Mango", "Grapes", "Pineapple", "Papaya", "Guava", "Pomegranate",
      "Cotton", "Sugarcane", "Groundnut", "Soybean", "Sunflower", "Mustard", "Linseed", "Peanut",
      "Rice", "Wheat", "Maize", "Barley", "Sorghum", "Millets", "Oats", "Ragi", "Bajra", "Jowar",
      "Tur", "Haldi", "Chilli", "Pepper", "Cumin", "Coriander", "Cardamom", "Clove", "Cinnamon", "Nutmeg"
    ];
  }
};