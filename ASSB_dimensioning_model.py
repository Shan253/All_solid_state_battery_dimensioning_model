import yaml
import math



class BatteryModel:
    def __init__(self, para_path):
        # Load parameters from YAML file
        self.para = self.load_parameter(para_path)
        self.dimensions = self.para['dimensions']
        self.material_properties = self.para['material_properties']
        self.densities = self.para['densities']
        self.thicknesses = self.para['thicknesses']
        self.battery_type = self.para.get('battery_type', {})
        self.battery_manufacturing_energy = self.para['battery_manufacturing_energy']
        
    @staticmethod
    def load_parameter(path):
        # Load and return parameters (dict)
        with open(path, 'r') as file:
            data = yaml.safe_load(file)
        # validate the 'battery_type' section here if necessary
        if 'battery_type' not in data:
            raise ValueError("Battery type is missing.")
        return data
        
    def update_parameters(self, updates):
            # Recursively update parameters to handle nested dictionary updates
        def recursive_update(orig_dict, new_updates):
            for key, value in new_updates.items():
                if isinstance(value, dict):
                    orig_dict[key] = recursive_update(orig_dict.get(key, {}), value)
                else:
                    orig_dict[key] = value
            return orig_dict

        self.para = recursive_update(self.para, updates)
        
    def get_anode_thickness(self, battery_type):
        # retrieve the anode thickness from 
        if 'ASSB' in battery_type:
            anode_thickness = self.thicknesses['anode'][battery_type]
        elif 'LIB' in battery_type:
            anode_thickness = self.calculate_LIBanode_thickness_single_layer(battery_type)['anode_thickness']   
        return anode_thickness
    
    def get_anode_density(self, battery_type):
    # Try to retrieve the cathode thickness from the parameters
        if 'ASSB' in battery_type:
            anode_density = self.densities['lithium']
        elif 'LIB' in battery_type:
            anode_density = self.calculate_LIBanode_thickness_single_layer(battery_type)['anode_density']
        return anode_density
    
    def calculate_LIBanode_thickness_single_layer(self, battery_type):
        # Calculation for anode thickness based on material properties and dimensions
        if 'LIB' not in battery_type:
            return {'anode_thickness': 'NA', 
                    'anode_density': 'NA',
                    'LIB_anode_void_volume': 'NA'
                    }
        else:
            pass  
       
        anode_area = self.calculate_component_areas()['anode_area']  # cm^2      ## single side area
        mass_loading = self.material_properties['mass_loading']['anode'][battery_type]   # mg/cm2   ## single side mass loading

        mass_anode_active = mass_loading * anode_area / 1000  # Convert mg to g    ## single side mass
        mass_anode = mass_anode_active / self.material_properties['ratio_cathode_active_material']     ## g    ## single side mass
        mass_anode_bc = mass_anode * self.material_properties['ratio_cathode_bc']        ## g  conductive_additive, black carbon    ## single side mass
        mass_anode_CMC_SBR = mass_anode * self.material_properties['ratio_cathode_pvdf']    ## g    ## single side mass

        volume_anode_active = mass_anode_active / self.densities['cam'][battery_type]    # cm^3    ## single side volume
        volume_anode_bc = mass_anode_bc / self.densities['black_carbon']   # cm^3     ## single side volume
        volume_anode_CMC_SBR = mass_anode_CMC_SBR / self.densities['CMC-SBR']   # cm^3         ## single side volume

        anode_material_volume = volume_anode_active + volume_anode_bc + volume_anode_CMC_SBR      # cm^3     ## single side volume
        processed_anode_volume = anode_material_volume / (1 - self.material_properties['porosity_cathode'])      # cm^3      ## single side volume
        
        LIB_anode_thickness = processed_anode_volume * 10 / anode_area     # thickness in mm      ## single side thickness
        LIB_anode_density = mass_anode / processed_anode_volume               # g/cm3    
        LIB_anode_void_volume = processed_anode_volume - anode_material_volume       ## single side volume

        return {'anode_thickness': LIB_anode_thickness, 
                'anode_density': LIB_anode_density,
                'LIB_anode_void_volume': LIB_anode_void_volume
                }  
      
        
    def calculate_cathode_thickness_single_layer(self, battery_type):
        # Calculation for cathode thickness based on material properties and dimensions
        cathode_area = self.calculate_component_areas()['cathode_area']  # cm^2   #the area per single layer
        mass_loading = self.material_properties['mass_loading']['cathode'][battery_type]   # mg/cm2

        mass_cathode_active = mass_loading * cathode_area / 1000  # Convert mg to g  #the amount per single layer
        mass_cathode = mass_cathode_active / self.material_properties['ratio_cathode_active_material']     ## g
        mass_cathode_bc = mass_cathode * self.material_properties['ratio_cathode_bc']        ## g  conductive_additive, black carbon
        mass_cathode_pvdf = mass_cathode * self.material_properties['ratio_cathode_pvdf']    ## g

        volume_cathode_active = mass_cathode_active / self.densities['cam'][battery_type]    # cm^3
        volume_cathode_bc = mass_cathode_bc / self.densities['black_carbon']   # cm^3  
        volume_cathode_pvdf = mass_cathode_pvdf / self.densities['PVDF']   # cm^3      

        cathode_material_volume = volume_cathode_active + volume_cathode_bc + volume_cathode_pvdf      # cm^3
        processed_cathode_volume = cathode_material_volume / (1 - self.material_properties['porosity_cathode'])      # cm^3
        
        cathode_thickness = processed_cathode_volume * 10 / cathode_area     # thickness in mm, one side coated for LIB
        cathode_density = mass_cathode/processed_cathode_volume               # g/cm3
        LIB_cathode_void_volume_single_layer = processed_cathode_volume - cathode_material_volume

        return {'cathode_thickness': cathode_thickness, 
                'cathode_density': cathode_density,
                'LIB_cathode_void_volume': LIB_cathode_void_volume_single_layer     ### cm3
                }    
        
        
    def calculate_all(self, battery_type):
        
        number_of_layers, cell_height = self.calculate_number_of_layers(battery_type)
        total_surface_area = self.calculate_total_surface_area(cell_height)
        cathode_density = self.calculate_cathode_thickness_single_layer(battery_type)['cathode_density']
        LIB_cathode_void_volume = self.calculate_cathode_thickness_single_layer(battery_type)['LIB_cathode_void_volume']
        if 'ASSB' in battery_type:
            LIB_anode_void_volume = 'NA'
        else:
            LIB_anode_void_volume = self.calculate_LIBanode_thickness_single_layer(battery_type)['LIB_anode_void_volume']
        
        intermediate_results = {  
            'cathode_density': cathode_density,
            'number_of_layers': number_of_layers,
            'cell_height': cell_height,                       #### mm
            'total_surface_area': total_surface_area,
            'LIB_cathode_void_volume': LIB_cathode_void_volume,  ### cm3
            'LIB_anode_void_volume': LIB_anode_void_volume      ### cm3
        }
        return intermediate_results    
    
    
    def calculate_number_of_layers(self, battery_type):
        # Calculate the number of layers based on the cell dimensions and material thicknesses
        available_height = self.dimensions['cell_height_benchmark'] - 2 * self.thicknesses['cell_container_thickness']
        cathode_thickness = self.calculate_cathode_thickness_single_layer(battery_type)['cathode_thickness']
        anode_thickness = self.get_anode_thickness(battery_type)
        if 'ASSB' in battery_type:    ##bipolar
            total_unit_thickness = (
            anode_thickness + 
            self.thicknesses['aluminum_foil'] +
            cathode_thickness +
            self.thicknesses['electrolyte'][battery_type])
        elif 'LIB' in battery_type:
            total_unit_thickness = (
            anode_thickness*2 +
            self.thicknesses['aluminum_foil'] +
            cathode_thickness*2 +
            self.thicknesses['copper_foil'] +
            self.thicknesses['separator'][battery_type]*2)


        number_of_layers = int(available_height / total_unit_thickness)
        cell_height = total_unit_thickness * number_of_layers  # Update cell height based on calculated layers, mm
        return number_of_layers, cell_height     
    
    def calculate_total_surface_area(self, cell_height):
        # Calculate the total surface area of the pouch cell needed for the casing material
        width = self.dimensions['total_cell']['width'] / 10  # Convert mm to cm
        length = self.dimensions['total_cell']['length'] / 10  # Convert mm to cm
        cell_height_cm = cell_height / 10  # Convert mm to cm
        # Calculate total surface area considering all sides of the pouch cell
        cell_surface_area = 2 * (width * length + width * cell_height_cm + length * cell_height_cm)  ## cm2
        return cell_surface_area
    
    def calculate_total_volume(self, cell_height):
        # Calculate the total volume of the pouch cell needed for the casing material
        electrolyte_length = self.dimensions['electrolyte']['length']   # mm
        electrolyte_width = self.dimensions['electrolyte']['width']  # mm
        length = (electrolyte_length + 2 * self.thicknesses['cell_container_thickness']) / 10   # Convert mm to cm, estimated real length
        width = (electrolyte_width + 2 * self.thicknesses['cell_container_thickness']) / 10      # Convert mm to cm, estimated real length 
        cell_height_cm = cell_height / 10  # Convert mm to cm
        # Calculate total surface area considering all sides of the pouch cell
        cell_volume = width * length * cell_height_cm       ## cm3
        return cell_volume    
    
    def calculate_pouch_cell(self, battery_type):
        # Calculate the material requirements for each component in the pouch cell
        all_calculations = self.calculate_all(battery_type)
        number_of_layers = all_calculations['number_of_layers'] 
        total_surface_area = all_calculations['total_surface_area']
        cathode_thickness = self.calculate_cathode_thickness_single_layer(battery_type)['cathode_thickness']  ## LIB cathode thickness is for single side coating
        cathode_density = all_calculations['cathode_density']
        anode_thickness = self.get_anode_thickness(battery_type)           ## LIB anode thickness is for single side coating
        anode_density = self.get_anode_density(battery_type)
        areas = self.calculate_component_areas()       ##
        cell_height = self.calculate_all(battery_type)['cell_height']
        cathode_material_capacity = self.material_properties['capacity_material'][battery_type]
        voltage = self.material_properties['voltage'][battery_type]
        
        # Calculate the mass of each component

        mass_cathode_current_collector_total = areas['current_collector_area'] * self.thicknesses['aluminum_foil'] * self.densities['aluminum'] / 10 * number_of_layers  # g
        mass_container_total = total_surface_area * self.thicknesses['cell_container_thickness'] * self.densities['cell_container_density'] / 10    # g
        mass_container_aluminium = total_surface_area * self.thicknesses['Al_layer'] * self.densities['aluminum'] / 10    # g
        mass_container_pet = total_surface_area * self.thicknesses['PET_layer'] * self.densities['PET'] / 10    # g
        mass_container_pp = mass_container_total - mass_container_aluminium - mass_container_pet      # g

        
        ## calcumate the cell volume  
        cell_volume = self.calculate_total_volume(cell_height)
        
        if 'LIB' in battery_type: 
            # Calculate the mass of cathode layer
            mass_cathode_total = areas['cathode_area'] * cathode_thickness * 2 * cathode_density/10 * number_of_layers   ## LIB cathode thickness is for single side coating
            
            # calculate the mass of anode layer
            mass_anode_total = areas['anode_area'] * anode_thickness * anode_density*2 / 10 * number_of_layers  # g   LIB anode thickness is for single side coating    ##thickness (mm)
            
            # Calculate the pouch cell void volume for electrolyte 
            separator_area = areas['current_collector_area']  ## assumed that separator has the same area as cc, single layer
            separator_thickness = self.thicknesses['separator'][battery_type]
            separator_porosity = self.material_properties['porosity_separator']
            separator_volume_total = 2* separator_area * separator_thickness/10 * number_of_layers   ## 2 separators in one repeating unit
            separator_void_volume_total = separator_volume_total * separator_porosity
            ### LIB cathode void volume
            LIB_cathode_void_volume_total = 2 * self.calculate_all(battery_type)['LIB_cathode_void_volume'] * number_of_layers
            LIB_anode_void_volume_total = 2 * self.calculate_all(battery_type)['LIB_anode_void_volume'] * number_of_layers
            LIB_cell_void_volume_total = separator_void_volume_total + LIB_cathode_void_volume_total + LIB_anode_void_volume_total                
            ### LIB cathode void volume       
            mass_aam_total = mass_anode_total * self.material_properties['ratio_cathode_active_material']   # g
            mass_anode_bc_total = mass_anode_total * self.material_properties['ratio_cathode_bc']             # g  conductive_additive, black carbon
            mass_anode_binder_total = mass_anode_total * self.material_properties['ratio_cathode_pvdf']    # g
            mass_anode_current_collector_total = areas['current_collector_area'] * self.thicknesses['copper_foil'] * self.densities['copper'] / 10 * number_of_layers  # g
            mass_liquid_electrolyte_total = LIB_cell_void_volume_total * self.densities['electrolyte'][battery_type]    ## g
            mass_separator_total =  separator_volume_total * self.densities['PP']
            total_cell_mass = mass_anode_total + mass_anode_current_collector_total + mass_cathode_current_collector_total + mass_cathode_total + mass_liquid_electrolyte_total + mass_separator_total + mass_container_total    # g
        elif 'ASSB' in battery_type:
            # Calculate the mass of each component
            mass_cathode_total = areas['cathode_area'] * cathode_thickness * cathode_density/10 * number_of_layers
            mass_anode_total = areas['anode_area'] * anode_thickness * anode_density / 10 * number_of_layers  # g   thickness (mm)
            mass_solid_electrolyte_total = areas['electrolyte_area'] * self.thicknesses['electrolyte'][battery_type] * self.densities['electrolyte'][battery_type] / 10 * number_of_layers  # g
            total_cell_mass = mass_anode_total + mass_cathode_current_collector_total + mass_cathode_total + mass_solid_electrolyte_total + mass_container_total    # g        
            


        ## calculate the cathode materials
        mass_cam_total = mass_cathode_total * self.material_properties['ratio_cathode_active_material']   # g
        mass_cathode_bc_total = mass_cathode_total * self.material_properties['ratio_cathode_bc']              # g conductive_additive, black carbon
        mass_cathode_binder_total = mass_cathode_total * self.material_properties['ratio_cathode_pvdf']    # g

        # Calculate battery capacity and specific energy based on the cathode material

        cell_capacity = mass_cam_total * cathode_material_capacity * voltage *0.001    # Wh
        specific_energy = cell_capacity / (total_cell_mass*0.001)     ## Wh/kg
        energy_density = cell_capacity / (cell_volume * 0.001)    ## converted cm3 to L, unit Wh/L
        
        if 'LIB' in battery_type:
            return {
            'Cathode': mass_cathode_total, 
            'Cathode active material': mass_cam_total, 
            'Cathode conductive additive': mass_cathode_bc_total, 
            'Cathode Binder': mass_cathode_binder_total, 
            'Anode': mass_anode_total, 
            'Anode active material': mass_aam_total, 
            'Anode conductive additive': mass_anode_bc_total, 
            'Anode Binder': mass_anode_binder_total,
            'Cathode current collector': mass_cathode_current_collector_total,
            'Anode current collector': mass_anode_current_collector_total,
            'Electrolyte': mass_liquid_electrolyte_total, 
            'Separator': mass_separator_total, 
            'Casing': mass_container_total,
            'Casing_al_layer': mass_container_aluminium,
            'Casing_al_pet': mass_container_pet,
            'Casing_al_pp': mass_container_pp, 
            'Total_mass': total_cell_mass,         ### g
            'Cell_capacity': cell_capacity, 
            'Specific_energy': specific_energy,
            'Energy_density': energy_density 
        }
        
        if 'ASSB' in battery_type:
            return {
            'Cathode': mass_cathode_total, 
            'Cathode active material': mass_cam_total, 
            'Cathode conductive additive': mass_cathode_bc_total, 
            'Cathode Binder': mass_cathode_binder_total, 
            'Anode active material': mass_anode_total, 
            'Cathode current collector': mass_cathode_current_collector_total, 
            'Electrolyte': mass_solid_electrolyte_total, 
            'Casing': mass_container_total,
            'Casing_al_layer': mass_container_aluminium,
            'Casing_al_pet': mass_container_pet,
            'Casing_al_pp': mass_container_pp,
            'Total_mass': total_cell_mass,         ### g
            'Cell_capacity': cell_capacity, 
            'Specific_energy': specific_energy,
            'Energy_density': energy_density,
            'cell_volume': cell_volume
        }
        
        

             
    def calculate_component_areas(self):
        cathode = self.dimensions['cathode']
        anode = self.dimensions['anode']
        electrolyte = self.dimensions['electrolyte']
        current_collector = self.dimensions['current_collector']
        

        return {
            'cathode_area': cathode['width'] * cathode['length'] / 100,  # cm^2
            'anode_area': anode['width'] * anode['length'] / 100,  # cm^2
            'electrolyte_area': electrolyte['width'] * electrolyte['length'] / 100,  # cm^2
            'current_collector_area': current_collector['width'] * current_collector['length'] / 100  # cm^ 
        }

    # Function to calculate the percentage composition of each component
    # the composition should be a dic, it is the results of calculate_pouch_cell
    def calculate_percentage_composition(self, battery_type):
        composition = self.calculate_pouch_cell(battery_type)
        total_mass = composition['Total_mass']  # Get the total mass from the dictionary
        percentage_composition = {}
        for component, mass in composition.items():
            if "_" not in component:  # do not calculate the battery performance values
                percentage = (mass / total_mass) * 100
                percentage_composition[component] = percentage
        return percentage_composition


    def manufacturing_energy(self, battery_type):
        ## access the relavant section in yaml file 
        anode_manu = self.battery_manufacturing_energy['electrode_manufacturing_anode']
        electrolyte_manu = self.battery_manufacturing_energy['electrolyte_manufacturing']
        cathode_manu = self.battery_manufacturing_energy['electrode_manufacturing_cathode']
        assembly_manu = self.battery_manufacturing_energy['assembly']
        formation_aging_manu = self.battery_manufacturing_energy['formation_and_aging']
        miscellaneous_manu = self.battery_manufacturing_energy['miscellaneous']
        ## the cell capacity of each batteries
        cell_capacity = self.calculate_pouch_cell(battery_type)['Cell_capacity']/1000   ## Wh transfered to kWh
        
        ## electricity and gas consumption of each processes for one cell, with unit of kWh
        
        Electrode_manufacturing_Anode_electrcity = anode_manu['electric_energy_consumption'][battery_type]*cell_capacity
        Electrode_manufacturing_Anode_gas = anode_manu['gas_consumption'][battery_type] * cell_capacity
        Electrode_manufacturing_Anode_total = Electrode_manufacturing_Anode_electrcity + Electrode_manufacturing_Anode_gas
        Electrolyte_manufacturing_electricity = electrolyte_manu ['electric_energy_consumption'][battery_type]*cell_capacity
        Electrolyte_manufacturing_gas = electrolyte_manu['gas_consumption'][battery_type]*cell_capacity
        Electrolyte_manufacturing_total = Electrolyte_manufacturing_electricity + Electrolyte_manufacturing_gas
        Electrode_manufacturing_cathode_electrcity = cathode_manu['electric_energy_consumption'][battery_type]*cell_capacity
        Electrode_manufacturing_cathode_gas = cathode_manu['gas_consumption'][battery_type]*cell_capacity
        Electrode_manufacturing_cathode_total = Electrode_manufacturing_cathode_electrcity + Electrode_manufacturing_cathode_gas
        Assembly_electricity = assembly_manu['electric_energy_consumption'][battery_type]*cell_capacity
        Assembly_gas = assembly_manu['gas_consumption'][battery_type]*cell_capacity
        Assembly_total = Assembly_electricity + Assembly_gas
        Formation_Aging_electricity = formation_aging_manu['electric_energy_consumption'][battery_type]*cell_capacity
        Formation_Aging_gas = formation_aging_manu['gas_consumption'][battery_type]*cell_capacity
        Formation_Aging_total = Formation_Aging_electricity + Formation_Aging_gas
        Miscellaneous_electricity = miscellaneous_manu['electric_energy_consumption'][battery_type]*cell_capacity
        Miscellaneous_gas = miscellaneous_manu['gas_consumption'][battery_type]*cell_capacity
        Miscellaneous_total = Miscellaneous_electricity + Miscellaneous_gas
        one_cell_man_energy = Electrode_manufacturing_Anode_total + Electrolyte_manufacturing_total + Electrode_manufacturing_cathode_total + Assembly_total + Formation_Aging_total + Miscellaneous_total
        
        return{
        'Anode_electricity': Electrode_manufacturing_Anode_electrcity,
        'Anode_gas': Electrode_manufacturing_Anode_gas,
        'Anode_total': Electrode_manufacturing_Anode_total, 
        'Electrolyte_electricity': Electrolyte_manufacturing_electricity, 
        'Electrolyte_gas': Electrolyte_manufacturing_gas, 
        'Electrolyte_total': Electrolyte_manufacturing_total, 
        'Cathode_electricity': Electrode_manufacturing_cathode_electrcity, 
        'Cathode_gas':Electrode_manufacturing_cathode_gas, 
        'Cathode_total': Electrode_manufacturing_cathode_total, 
        'Assembly_electricity': Assembly_electricity, 
        'Assembly_gas': Assembly_gas, 
        'Assembly_total': Assembly_total, 
        'Formation_Aging_electricity': Formation_Aging_electricity, 
        'Formation_Aging_gas': Formation_Aging_gas, 
        'Formation_Aging_total': Formation_Aging_total, 
        'Miscellaneous_electricity':Miscellaneous_electricity, 
        'Miscellaneous_gas':Miscellaneous_gas, 
        'Miscellaneous_total':Miscellaneous_total,
        'one_cell_man_energy': one_cell_man_energy  
        }

