document.addEventListener('DOMContentLoaded', function () {
     const citySelect = document.querySelector('#id_city');
     const fromRegionSelect = document.querySelector('#id_fromRegion');
     const toRegionSelect = document.querySelector('#id_toRegion');

     if (!citySelect || !fromRegionSelect || !toRegionSelect) return;

     citySelect.addEventListener('change', function () {
          const cityId = this.value;
          if (!cityId) {
               updateOptions(fromRegionSelect, []);
               updateOptions(toRegionSelect, []);
               return;
          }

          fetch(`/api/subregions/${cityId}/`)
               .then(response => response.json())
               .then(data => {
                    if (data.success) {
                         updateOptions(fromRegionSelect, data.subregions);
                         updateOptions(toRegionSelect, data.subregions);
                    }
               })
               .catch(error => console.error('Error fetching subregions:', error));
     });

     function updateOptions(selectElement, options) {
          const currentValue = selectElement.value;
          // Keep the "--------- " empty option
          selectElement.innerHTML = '<option value="">--------- </option>';

          options.forEach(opt => {
               const option = document.createElement('option');
               option.value = opt.id;
               option.textContent = opt.name;
               if (opt.id.toString() === currentValue) {
                    option.selected = true;
               }
               selectElement.appendChild(option);
          });
     }
});
